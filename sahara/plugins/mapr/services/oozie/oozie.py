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


from oslo_log import log as logging
import six

import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.mysql.mysql as mysql
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.validation_utils as vu


LOG = logging.getLogger(__name__)

OOZIE = np.NodeProcess(
    name='oozie',
    ui_name='Oozie',
    package='mapr-oozie',
    open_ports=[11000]
)


@six.add_metaclass(s.Single)
class Oozie(s.Service):
    def __init__(self):
        super(Oozie, self).__init__()
        self._name = 'oozie'
        self._ui_name = 'Oozie'
        self._node_processes = [OOZIE]
        self._cluster_defaults = ['oozie-default.json']
        self._validation_rules = [vu.exactly(1, OOZIE)]
        self._ui_info = [('Oozie', OOZIE, 'http://%s:11000/oozie')]

    def get_config_files(self, cluster_context, configs, instance=None):
        oozie_site = bcf.HadoopXML("oozie-site.xml")
        oozie_site.remote_path = self.conf_dir(cluster_context)
        if instance:
            oozie_site.fetch(instance)
        oozie_site.load_properties(configs)
        oozie_site.add_properties(self._get_oozie_site_props(cluster_context))
        return [oozie_site]

    def _get_oozie_site_props(self, context):
        oozie_specs = mysql.MySQL.OOZIE_SPECS

        return {
            'oozie.db.schema.name': oozie_specs.db_name,
            'oozie.service.JPAService.create.db.schema': True,
            'oozie.service.JPAService.jdbc.driver': mysql.MySQL.DRIVER_CLASS,
            'oozie.service.JPAService.jdbc.url': self._get_jdbc_uri(context),
            'oozie.service.JPAService.jdbc.username': oozie_specs.user,
            'oozie.service.JPAService.jdbc.password': oozie_specs.password,
            'oozie.service.HadoopAccessorService.hadoop.configurations':
                '*=%s' % context.hadoop_conf
        }

    def _get_jdbc_uri(self, context):
        jdbc_uri = ('jdbc:mysql://%(db_host)s:%(db_port)s/%(db_name)s?'
                    'createDatabaseIfNotExist=true')
        jdbc_args = {
            'db_host': mysql.MySQL.get_db_instance(context).internal_ip,
            'db_port': mysql.MySQL.MYSQL_SERVER_PORT,
            'db_name': mysql.MySQL.OOZIE_SPECS.db_name,
        }
        return jdbc_uri % jdbc_args

    def post_install(self, cluster_context, instances):
        oozie_inst = cluster_context.get_instance(OOZIE)
        oozie_service = cluster_context.get_service(OOZIE)
        if oozie_service:
            oozie_version = oozie_service.version
            symlink_cmd = ('cp /usr/share/java/mysql-connector-java.jar '
                           '/opt/mapr/oozie/oozie-%s'
                           '/oozie-server/lib/') % oozie_version
            with oozie_inst.remote() as r:
                LOG.debug('Installing MySQL connector for Oozie')
                r.execute_command(symlink_cmd, run_as_root=True,
                                  raise_when_error=False)

    def _install_share_libs(self, cluster_context):
        check_sharelib = 'sudo -u mapr hadoop fs -ls /oozie/share/lib'
        create_sharelib_dir = 'sudo -u mapr hadoop fs -mkdir /oozie'
        is_yarn = cluster_context.cluster_mode == 'yarn'
        upload_args = {
            'oozie_home': self.home_dir(cluster_context),
            'share': 'share2' if is_yarn else 'share1'
        }
        upload_sharelib = ('sudo -u mapr hadoop fs -copyFromLocal '
                           '%(oozie_home)s/%(share)s /oozie/share')
        oozie_inst = cluster_context.get_instance(OOZIE)
        with oozie_inst.remote() as r:
            LOG.debug("Installing Oozie sharelibs")
            command = '%(check)s || (%(mkdir)s && %(upload)s)'
            args = {
                'check': check_sharelib,
                'mkdir': create_sharelib_dir,
                'upload': upload_sharelib % upload_args,
            }
            r.execute_command(command % args, raise_when_error=False)

    def post_start(self, cluster_context, instances):
        instances = cluster_context.filter_instances(instances, OOZIE)
        self._install_share_libs(cluster_context)
        self._install_ui(cluster_context, instances)

    @g.remote_command(1)
    def _rebuild_oozie_war(self, remote, cluster_context):
        extjs_url = 'http://dev.sencha.com/deploy/ext-2.2.zip'
        extjs_file = '/tmp/extjs.zip'
        g.download(remote, extjs_url, extjs_file)
        cmd = '%(home)s/bin/oozie-setup.sh prepare-war -extjs %(ext)s'
        args = {'home': self.home_dir(cluster_context), 'ext': extjs_file}
        remote.execute_command(cmd % args, run_as_root=True)

    def update(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        instances = cluster_context.filter_instances(instances, OOZIE)
        self._install_ui(cluster_context, instances)

    def _install_ui(self, cluster_context, instances):
        OOZIE.stop(filter(OOZIE.is_started, instances))
        g.execute_on_instances(
            instances, self._rebuild_oozie_war, cluster_context)
        OOZIE.start(instances)


@six.add_metaclass(s.Single)
class OozieV401(Oozie):
    def __init__(self):
        super(OozieV401, self).__init__()
        self._version = '4.0.1'
        self._dependencies = [('mapr-oozie-internal', self.version)]


@six.add_metaclass(s.Single)
class OozieV410(Oozie):
    def __init__(self):
        super(OozieV410, self).__init__()
        self._version = '4.1.0'
        self._dependencies = [('mapr-oozie-internal', self.version)]
