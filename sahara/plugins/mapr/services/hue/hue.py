# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import itertools
import random
import string

from oslo_log import log as logging
import six

import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.hbase.hbase as hbase
import sahara.plugins.mapr.services.hive.hive as hive
import sahara.plugins.mapr.services.httpfs.httpfs as httpfs
import sahara.plugins.mapr.services.impala.impala as impala
import sahara.plugins.mapr.services.mapreduce.mapreduce as mr
import sahara.plugins.mapr.services.mysql.mysql as mysql
import sahara.plugins.mapr.services.oozie.oozie as oozie
import sahara.plugins.mapr.services.sqoop.sqoop2 as sqoop
import sahara.plugins.mapr.services.yarn.yarn as yarn
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.utils.files as files


LOG = logging.getLogger(__name__)

HUE = np.NodeProcess(
    name='hue',
    ui_name='Hue',
    package='mapr-hue',
    open_ports=[8002, 8888]
)


@six.add_metaclass(s.Single)
class Hue(s.Service):
    def __init__(self):
        super(Hue, self).__init__()
        self._name = 'hue'
        self._ui_name = 'Hue'
        self._version = '3.6.0'
        self._node_processes = [HUE]
        self._ui_info = [('HUE', HUE, 'http://%s:8888')]
        self._validation_rules = [vu.on_same_node(HUE, httpfs.HTTP_FS)]

    def conf_dir(self, cluster_context):
        return '%s/desktop/conf' % self.home_dir(cluster_context)

    def get_config_files(self, cluster_context, configs, instance=None):
        template = 'plugins/mapr/services/hue/resources/hue_3.6.0.template'

        hue_ini = bcf.TemplateFile("hue.ini")
        hue_ini.remote_path = self.conf_dir(cluster_context)
        hue_ini.parse(files.get_file_text(template))
        hue_ini.add_properties(self._get_hue_ini_props(cluster_context))

        # TODO(aosadchyi): rewrite it
        hue_instances = cluster_context.get_instances(HUE)
        for instance in hue_instances:
            if instance not in cluster_context.changed_instances():
                cluster_context.should_be_restarted[self] += [instance]

        return [hue_ini]

    def _get_hue_ini_props(self, context):
        db_instance = mysql.MySQL.get_db_instance(context)
        is_yarn = context.cluster_mode == 'yarn'
        hue_specs = mysql.MySQL.HUE_SPECS
        rdbms_specs = mysql.MySQL.RDBMS_SPECS

        result = {
            'db_host': db_instance.fqdn(),
            'hue_name': hue_specs.db_name,
            'hue_user': hue_specs.user,
            'hue_password': hue_specs.password,
            'rdbms_name': rdbms_specs.db_name,
            'rdbms_user': rdbms_specs.user,
            'rdbms_password': rdbms_specs.password,
            'resource_manager_uri': context.resource_manager_uri,
            'yarn_mode': is_yarn,
            'rm_host': context.get_instance_ip(yarn.RESOURCE_MANAGER),
            'webhdfs_url': context.get_instance_ip(httpfs.HTTP_FS),
            'jt_host': context.get_instance_ip(mr.JOB_TRACKER),
            'oozie_host': context.get_instance_ip(oozie.OOZIE),
            'sqoop_host': context.get_instance_ip(sqoop.SQOOP_2_SERVER),
            'impala_host': context.get_instance_ip(impala.IMPALA_STATE_STORE),
            'hbase_host': context.get_instance_ip(hbase.HBASE_THRIFT),
            'zk_hosts_with_port': context.get_zookeeper_nodes_ip_with_port(),
            'secret_key': self._generate_secret_key(),
        }

        hive_host = context.get_instance(hive.HIVE_METASTORE)
        if hive_host:
            hive_service = context.get_service(hive.HIVE_METASTORE)
            result.update({
                'hive_host': hive_host.management_ip,
                'hive_version': hive_service.version,
                'hive_conf_dir': hive_service.conf_dir(context),
            })

        return result

    def post_install(self, cluster_context, instances):
        hue_instance = cluster_context.get_instance(HUE)

        def migrate_database(remote, context):
            hue_service = context.get_service(HUE)
            hue_home = '/opt/mapr/hue/hue-%s' % hue_service.version
            cmd = '%(activate)s && %(syncdb)s && %(migrate)s'
            args = {
                'activate': 'source %s/build/env/bin/activate' % hue_home,
                'syncdb': '%s/build/env/bin/hue syncdb --noinput' % hue_home,
                'migrate': '%s/build/env/bin/hue migrate' % hue_home,
            }
            remote.execute_command(cmd % args, run_as_root=True, timeout=600)

        def set_owner(remote):
            remote.execute_command('chown -R mapr:mapr /opt/mapr/hue',
                                   run_as_root=True)

        if hue_instance:
            with hue_instance.remote() as r:
                LOG.debug("Executing Hue database migration")
                migrate_database(r, cluster_context)
                LOG.debug("Changing Hue home dir owner")
                set_owner(r)
            self._copy_hive_configs(cluster_context, hue_instance)
            self._install_jt_plugin(cluster_context, hue_instance)

    def _copy_hive_configs(self, cluster_context, hue_instance):
        hive_server = cluster_context.get_instance(hive.HIVE_SERVER_2)
        if not hive_server or hive_server == hue_instance:
            LOG.debug('No Hive Servers found. Skip')
            return
        hive_service = cluster_context.get_service(hive.HIVE_SERVER_2)
        hive_conf_dir = hive_service.conf_dir(cluster_context)
        g.copy(hive_conf_dir, hive_server, hive_conf_dir, hue_instance, 'root')

    def update(self, cluster_context, instances=None):
        if self._should_restart(cluster_context, instances):
            hue_instance = cluster_context.get_instance(HUE)
            self.restart([hue_instance])

    def _should_restart(self, c_context, instances):
        app_services = [
            impala.Impala(),
            hive.Hive(),
            hbase.HBase(),
            sqoop.Sqoop2(),
        ]
        instances = [c_context.filter_instances(instances, service=service)
                     for service in app_services]
        return bool(g.unique_list(itertools.chain(*instances)))

    def jt_plugin_path(self, cluster_context):
        path = ('%(home)s/desktop/libs/hadoop/java-lib'
                '/hue-plugins-%(version)s-mapr.jar')
        args = {
            'home': self.home_dir(cluster_context),
            'version': self.version,
        }
        return path % args

    def _install_jt_plugin(self, cluster_context, hue_instance):
        LOG.debug("Copying Hue JobTracker plugin")
        job_trackers = cluster_context.get_instances(mr.JOB_TRACKER)
        if not job_trackers:
            LOG.debug('No JobTrackers found. Skip')
            return
        jt_plugin_src = self.jt_plugin_path(cluster_context)
        jt_plugin_dest = cluster_context.hadoop_lib + '/jt_plugin.jar'
        for jt in job_trackers:
            g.copy(jt_plugin_src, hue_instance, jt_plugin_dest, jt, 'root')

    def _generate_secret_key(self, length=80):
        ascii_alphanum = string.ascii_letters + string.digits
        generator = random.SystemRandom()
        return ''.join(generator.choice(ascii_alphanum) for _ in range(length))
