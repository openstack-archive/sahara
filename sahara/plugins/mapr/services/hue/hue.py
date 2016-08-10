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

from sahara.i18n import _
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
import sahara.plugins.mapr.services.sentry.sentry as sentry
import sahara.plugins.mapr.services.spark.spark as spark
import sahara.plugins.mapr.services.sqoop.sqoop2 as sqoop
import sahara.plugins.mapr.services.yarn.yarn as yarn
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.password_utils as pu
from sahara.plugins.mapr.util import service_utils as su
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.plugins.provisioning as p
import sahara.utils.files as files

LOG = logging.getLogger(__name__)

HUE = np.NodeProcess(
    name='hue',
    ui_name='Hue',
    package='mapr-hue',
    open_ports=[8002, 8888]
)

HUE_LIVY = np.NodeProcess(
    name="livy",
    ui_name="Hue Livy",
    package="mapr-hue-livy",
    open_ports=[8998]
)


class Hue(s.Service):
    THRIFT_VERSIONS = [5, 7]
    THRIFT_VERSION = p.Config(
        name="Thrift version",
        applicable_target="Hue",
        scope='cluster',
        config_type="dropdown",
        config_values=[(v, v) for v in THRIFT_VERSIONS],
        priority=1,
        description=_(
            'Specifies thrift version.')
    )

    def __init__(self):
        super(Hue, self).__init__()
        self._name = 'hue'
        self._ui_name = 'Hue'
        self._node_processes = [HUE]
        self._ui_info = None
        self._validation_rules = [
            vu.exactly(1, HUE),
            vu.on_same_node(HUE, httpfs.HTTP_FS),
            vu.on_same_node(HUE_LIVY, spark.SPARK_SLAVE),
        ]
        self._priority = 2

    def get_ui_info(self, cluster_context):
        # Hue uses credentials of the administrative user (PAM auth)
        return [('HUE', HUE, {s.SERVICE_UI: 'http://%s:8888',
                              'Username': 'mapr',
                              'Password': pu.get_mapr_password(cluster_context
                                                               .cluster)})]

    def get_configs(self):
        return [Hue.THRIFT_VERSION]

    def conf_dir(self, cluster_context):
        return '%s/desktop/conf' % self.home_dir(cluster_context)

    def get_config_files(self, cluster_context, configs, instance=None):
        template = 'plugins/mapr/services/hue/resources/hue_%s.template'
        # hue.ini
        hue_ini = bcf.TemplateFile("hue.ini")
        hue_ini.remote_path = self.conf_dir(cluster_context)
        hue_ini.parse(files.get_file_text(template % self.version))
        hue_ini.add_properties(self._get_hue_ini_props(cluster_context))
        hue_ini.add_property("thrift_version",
                             configs[self.THRIFT_VERSION.name])

        # # hue.sh
        hue_sh_template = 'plugins/mapr/services/hue/' \
                          'resources/hue_sh_%s.template'
        hue_sh = bcf.TemplateFile("hue.sh")
        hue_sh.remote_path = self.home_dir(cluster_context) + '/bin'
        hue_sh.parse(files.get_file_text(hue_sh_template % self.version))
        hue_sh.add_property('hadoop_version', cluster_context.hadoop_version)
        hue_sh.mode = 777

        hue_instances = cluster_context.get_instances(HUE)
        for instance in hue_instances:
            if instance not in cluster_context.changed_instances():
                cluster_context.should_be_restarted[self] += [instance]

        return [hue_ini, hue_sh]

    def _get_hue_ini_props(self, cluster_context):
        db_instance = mysql.MySQL.get_db_instance(cluster_context)
        is_yarn = cluster_context.cluster_mode == 'yarn'
        hue_specs = mysql.MySQL.HUE_SPECS
        rdbms_specs = mysql.MySQL.RDBMS_SPECS

        result = {
            'db_host': db_instance.internal_ip,
            'hue_name': hue_specs.db_name,
            'hue_user': hue_specs.user,
            'hue_password': hue_specs.password,
            'rdbms_name': rdbms_specs.db_name,
            'rdbms_user': rdbms_specs.user,
            'rdbms_password': rdbms_specs.password,
            'resource_manager_uri': cluster_context.resource_manager_uri,
            'yarn_mode': is_yarn,
            'rm_host': cluster_context.get_instance_ip(yarn.RESOURCE_MANAGER),
            'webhdfs_url': cluster_context.get_instance_ip(httpfs.HTTP_FS),
            'jt_host': cluster_context.get_instance_ip(mr.JOB_TRACKER),
            'oozie_host': cluster_context.get_instance_ip(oozie.OOZIE),
            'sqoop_host': cluster_context.get_instance_ip(
                sqoop.SQOOP_2_SERVER),
            'impala_host': cluster_context.get_instance_ip(
                impala.IMPALA_STATE_STORE),
            'zk_hosts_with_port':
                cluster_context.get_zookeeper_nodes_ip_with_port(),
            'secret_key': self._generate_secret_key()
        }

        hive_host = cluster_context.get_instance(hive.HIVE_SERVER_2)
        if hive_host:
            hive_service = cluster_context.get_service(hive.HIVE_SERVER_2)
            result.update({
                'hive_host': hive_host.internal_ip,
                'hive_version': hive_service.version,
                'hive_conf_dir': hive_service.conf_dir(cluster_context),
            })

        hbase_host = cluster_context.get_instance(hbase.HBASE_THRIFT)
        if hbase_host:
            hbase_service = cluster_context.get_service(hbase.HBASE_THRIFT)
            result.update({
                'hbase_host': hbase_host.internal_ip,
                'hbase_conf_dir': hbase_service.conf_dir(cluster_context),
            })

        livy_host = cluster_context.get_instance(HUE_LIVY)
        if livy_host:
            result.update({
                'livy_host': livy_host.internal_ip
            })

        sentry_host = cluster_context.get_instance(sentry.SENTRY)
        if sentry_host:
            ui_name = sentry.Sentry().ui_name
            sentry_version = cluster_context.get_chosen_service_version(
                ui_name)
            sentry_service = cluster_context. \
                _find_service_instance(ui_name, sentry_version)
            result.update({
                'sentry_host': sentry_host.internal_ip,
                'sentry_conf': sentry_service.conf_dir(cluster_context)
            })

        return result

    def post_install(self, cluster_context, instances):
        hue_instance = cluster_context.get_instance(HUE)

        def migrate_database(remote, cluster_context):
            hue_home = self.home_dir(cluster_context)
            cmd = '%(activate)s && %(syncdb)s && %(migrate)s'
            args = {
                'activate': 'source %s/build/env/bin/activate' % hue_home,
                'syncdb': '%s/build/env/bin/hue syncdb --noinput' % hue_home,
                'migrate': '%s/build/env/bin/hue migrate' % hue_home,
            }
            remote.execute_command(cmd % args, run_as_root=True, timeout=600)

        def hue_syncdb_workround(remote):
            cmd = 'printf "/opt/mapr/lib\n$JAVA_HOME/jre/lib/amd64/server\n"' \
                  ' | tee /etc/ld.so.conf.d/mapr-hue.conf && ldconfig'
            remote.execute_command(cmd, run_as_root=True)

        with hue_instance.remote() as r:
            LOG.debug("Executing Hue database migration")
            # temporary workaround to prevent failure of db migrate on mapr 5.2
            hue_syncdb_workround(r)
            migrate_database(r, cluster_context)
        self._copy_hive_configs(cluster_context, hue_instance)
        self._install_jt_plugin(cluster_context, hue_instance)
        self._set_service_dir_owner(cluster_context, instances)

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

    def post_start(self, cluster_context, instances):
        self.update(cluster_context, instances=instances)

    def restart(self, instances):
        for node_process in [HUE]:
            filtered_instances = su.filter_by_node_process(instances,
                                                           node_process)
            if filtered_instances:
                node_process.restart(filtered_instances)

    def _should_restart(self, cluster_context, instances):
        app_services = [
            impala.Impala(),
            hive.Hive(),
            hbase.HBase(),
            sqoop.Sqoop2(),
            spark.SparkOnYarn(),
        ]
        instances = [
            cluster_context.filter_instances(instances, service=service)
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


class HueV360(Hue):
    def __init__(self):
        super(HueV360, self).__init__()
        self._version = '3.6.0'


class HueV370(Hue):
    def __init__(self):
        super(HueV370, self).__init__()
        self._version = '3.7.0'


class HueV381(Hue):
    def __init__(self):
        super(HueV381, self).__init__()
        self._version = "3.8.1"
        self._dependencies = [("mapr-hue-base", self.version)]
        self._node_processes = [HUE, HUE_LIVY]
        self._validation_rules.append(vu.at_most(1, HUE_LIVY))


class HueV390(Hue):
    def __init__(self):
        super(HueV390, self).__init__()
        self._version = "3.9.0"
        self._dependencies = [("mapr-hue-base", self.version)]
        self._node_processes = [HUE, HUE_LIVY]
        self._validation_rules.append(vu.at_most(1, HUE_LIVY))
