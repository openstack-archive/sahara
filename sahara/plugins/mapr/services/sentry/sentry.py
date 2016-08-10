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

from sahara.i18n import _
import sahara.plugins.mapr.domain.configuration_file as cf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.mysql.mysql as mysql
import sahara.plugins.mapr.util.maprfs_helper as mfs
import sahara.plugins.provisioning as p
import sahara.utils.files as files

SENTRY = np.NodeProcess(
    name='sentry',
    ui_name='Sentry',
    package='mapr-sentry'
)

SENTRY_MODE_CONFIG_NAME = 'Sentry storage mode'
FILE_STORAGE_SENTRY_MODE = 'File-base storage'
DB_STORAGE_SENTRY_MODE = 'DB-based storage'


class Sentry(s.Service):
    SENTRY_STORAGE_MODE = p.Config(
        name=SENTRY_MODE_CONFIG_NAME,
        applicable_target='Sentry',
        scope='cluster',
        config_type="dropdown",
        config_values=[(v, v) for v in
                       (FILE_STORAGE_SENTRY_MODE, DB_STORAGE_SENTRY_MODE)],
        priority=1,
        description=_(
            'Specifies Sentry storage mode.')
    )
    GLOBAL_POLICY_FILE = '/user/mapr/sentry/global-policy.ini'

    def __init__(self):
        super(Sentry, self).__init__()
        self._name = 'sentry'
        self._ui_name = 'Sentry'
        self._node_processes = [SENTRY]
        self._priority = 2

    def get_configs(self):
        return [Sentry.SENTRY_STORAGE_MODE]

    def get_config_files(self, cluster_context, configs, instance=None):
        sentry_default =\
            'plugins/mapr/services/sentry/resources/sentry-default.xml'
        global_policy_template =\
            'plugins/mapr/services/sentry/resources/global-policy.ini'
        sentry_site = cf.HadoopXML('sentry-site.xml')
        sentry_site.remote_path = self.conf_dir(cluster_context)
        if instance:
            sentry_site.fetch(instance)
        sentry_site.load_properties(configs)
        sentry_mode = configs[self.SENTRY_STORAGE_MODE.name]
        sentry_site.parse(files.get_file_text(sentry_default))
        sentry_site.add_properties(
            self._get_sentry_site_props(cluster_context, sentry_mode))
        global_policy = cf.TemplateFile('global-policy.ini')
        global_policy.remote_path = self.conf_dir(cluster_context)
        global_policy.parse(files.get_file_text(global_policy_template))
        return [sentry_site, global_policy]

    def _get_jdbc_uri(self, cluster_context):
        jdbc_uri = ('jdbc:mysql://%(db_host)s:%(db_port)s/%(db_name)s?'
                    'createDatabaseIfNotExist=true')
        jdbc_args = {
            'db_host': mysql.MySQL.get_db_instance(
                cluster_context).internal_ip,
            'db_port': mysql.MySQL.MYSQL_SERVER_PORT,
            'db_name': mysql.MySQL.SENTRY_SPECS.db_name,
        }
        return jdbc_uri % jdbc_args

    def _get_sentry_site_props(self, cluster_context, setry_mode):
        sentry_specs = mysql.MySQL.SENTRY_SPECS
        if setry_mode == FILE_STORAGE_SENTRY_MODE:
            return {
                'sentry.hive.provider.backend':
                    'org.apache.sentry.provider'
                    '.file.SimpleFileProviderBackend',
                'sentry.hive.provider.resource':
                    'maprfs:///' + self.GLOBAL_POLICY_FILE,
            }
        if setry_mode == DB_STORAGE_SENTRY_MODE:
            return {
                'sentry.hive.provider.backend':
                    'org.apache.sentry.provider.db.SimpleDBProviderBackend',
                'sentry.store.jdbc.url': self._get_jdbc_uri(cluster_context),
                'sentry.store.jdbc.driver': mysql.MySQL.DRIVER_CLASS,
                'sentry.store.jdbc.user': sentry_specs.user,
                'sentry.store.jdbc.password': sentry_specs.password,
            }

    def _init_db_schema(self, cluster_context):
        instance = cluster_context.get_instance(SENTRY)
        cmd = '%(home)s/bin/sentry --command schema-tool' \
              ' --conffile %(home)s/conf/sentry-site.xml' \
              ' --dbType mysql --initSchema' % {
                  'home': self.home_dir(cluster_context)}
        with instance.remote() as r:
            r.execute_command(cmd, run_as_root=True)

    def post_start(self, cluster_context, instances):
        sentry_host = cluster_context.get_instance(SENTRY)
        source = self.conf_dir(cluster_context) + '/global-policy.ini'
        with sentry_host.remote() as r:
            mfs.mkdir(r, '/user/mapr/sentry', run_as='mapr')
            mfs.chmod(r, '/user/mapr/sentry', 777, run_as='mapr')
            mfs.copy_from_local(r, source, self.GLOBAL_POLICY_FILE,
                                hdfs_user='mapr')

    def _copy_warden_conf(self, cluster_context):
        sentry_host = cluster_context.get_instance(SENTRY)
        cmd = 'sudo -u mapr cp %s/conf.d/warden.sentry.conf' \
              ' /opt/mapr/conf/conf.d/' % self.home_dir(cluster_context)
        with sentry_host.remote() as r:
            r.execute_command(cmd)

    def post_install(self, cluster_context, instances):
        self._set_service_dir_owner(cluster_context, instances)
        if cluster_context._get_cluster_config_value(
                self.SENTRY_STORAGE_MODE) == DB_STORAGE_SENTRY_MODE:
            self._init_db_schema(cluster_context)
            self._copy_warden_conf(cluster_context)

    def supports(self, service, mode):
        "return True is Sentry supports integration"
        service = service.name + '-' + service.version
        return self.SENTRY_SUPPORT_MATRIX[mode][service]


class SentryV16(Sentry):
    SENTRY_SUPPORT_MATRIX = {
        DB_STORAGE_SENTRY_MODE: {
            'hive-1.2': True,
            'hive-2.0': True,
            'impala-2.2.0': True,
            'impala-2.5.0': True
        },
        FILE_STORAGE_SENTRY_MODE: {
            'hive-1.2': True,
            'hive-2.0': True,
            'impala-2.2.0': True,
            'impala-2.5.0': True
        },
    }

    def __init__(self):
        super(SentryV16, self).__init__()
        self._version = '1.6.0'
