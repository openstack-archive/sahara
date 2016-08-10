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

import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.sentry.sentry as sentry
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.utils.files as files

LOG = logging.getLogger(__name__)

HIVE_METASTORE = np.NodeProcess(
    name='hivemeta',
    ui_name='HiveMetastore',
    package='mapr-hivemetastore',
    open_ports=[9083]
)
HIVE_SERVER_2 = np.NodeProcess(
    name='hs2',
    ui_name='HiveServer2',
    package='mapr-hiveserver2',
    open_ports=[10000]
)


class Hive(s.Service):
    def __init__(self):
        super(Hive, self).__init__()
        self._name = 'hive'
        self._ui_name = 'Hive'
        self._node_processes = [HIVE_METASTORE, HIVE_SERVER_2]
        self._validation_rules = [
            vu.exactly(1, HIVE_METASTORE),
            vu.exactly(1, HIVE_SERVER_2),
        ]

    # hive-site.xml
    def get_config_files(self, cluster_context, configs, instance=None):
        hive_default = 'plugins/mapr/services/hive/resources/hive-default.xml'
        hive_site = bcf.HadoopXML("hive-site.xml")
        hive_site.remote_path = self.conf_dir(cluster_context)
        if instance:
            hive_site.fetch(instance)
        hive_site.parse(files.get_file_text(hive_default))
        hive_site.add_properties(self._get_hive_site_props(cluster_context))
        sentry_host = cluster_context.get_instance(sentry.SENTRY)
        if sentry_host:
            sentry_mode = cluster_context._get_cluster_config_value(
                sentry.Sentry().SENTRY_STORAGE_MODE)
            ui_name = sentry.Sentry().ui_name
            sentry_version = cluster_context.get_chosen_service_version(
                ui_name)
            sentry_service = cluster_context. \
                _find_service_instance(ui_name, sentry_version)
            if sentry_service.supports(self, sentry_mode):
                sentry_default = 'plugins/mapr/services/hive/resources/' \
                                 'sentry-default.xml'
                sentry_db = \
                    'plugins/mapr/services/hive/resources/sentry-db.xml'
                hive_site.parse(files.get_file_text(sentry_default))
                hive_site.add_property('hive.sentry.conf.url',
                                       'file://%s/sentry-site.xml' %
                                       sentry_service.conf_dir(
                                           cluster_context))
                if sentry_mode == sentry.DB_STORAGE_SENTRY_MODE:
                    hive_site.parse(files.get_file_text(sentry_db))

        return [hive_site]

    def _get_hive_site_props(self, cluster_context):
        # Import here to resolve circular dependency
        from sahara.plugins.mapr.services.mysql import mysql

        zookeepers = cluster_context.get_zookeeper_nodes_ip()
        metastore_specs = mysql.MySQL.METASTORE_SPECS

        return {
            'javax.jdo.option.ConnectionDriverName': mysql.MySQL.DRIVER_CLASS,
            'javax.jdo.option.ConnectionURL': self._get_jdbc_uri(
                cluster_context),
            'javax.jdo.option.ConnectionUserName': metastore_specs.user,
            'javax.jdo.option.ConnectionPassword': metastore_specs.password,
            'hive.metastore.uris': self._get_metastore_uri(cluster_context),
            'hive.zookeeper.quorum': zookeepers,
            'hbase.zookeeper.quorum': zookeepers,
        }

    def _get_jdbc_uri(self, cluster_context):
        # Import here to resolve circular dependency
        from sahara.plugins.mapr.services.mysql import mysql

        jdbc_uri = ('jdbc:mysql://%(db_host)s:%(db_port)s/%(db_name)s?'
                    'createDatabaseIfNotExist=true')
        jdbc_args = {
            'db_host': mysql.MySQL.get_db_instance(
                cluster_context).internal_ip,
            'db_port': mysql.MySQL.MYSQL_SERVER_PORT,
            'db_name': mysql.MySQL.METASTORE_SPECS.db_name,
        }
        return jdbc_uri % jdbc_args

    def _get_metastore_uri(self, cluster_context):
        return 'thrift://%s:9083' % cluster_context.get_instance_ip(
            HIVE_METASTORE)

    def post_start(self, cluster_context, instances):
        # Import here to resolve circular dependency
        import sahara.plugins.mapr.services.maprfs.maprfs as mfs

        create_path = lambda p: 'sudo -u mapr hadoop fs -mkdir %s' % p
        check_path = 'sudo -u mapr hadoop fs -ls %s'
        cmd = "%(check)s || ( %(parent)s && %(target)s )"
        args = {
            'check': check_path % '/user/hive/warehouse/',
            'parent': create_path('/user/hive/'),
            'target': create_path('/user/hive/warehouse/')
        }
        cldb_node = cluster_context.get_instance(mfs.CLDB)
        with cldb_node.remote() as r:
            LOG.debug("Creating Hive warehouse dir")
            r.execute_command(cmd % args, raise_when_error=False)
        self._create_sentry_role(cluster_context)

    def _create_sentry_role(self, cluster_context):
        instance = cluster_context.get_instance(HIVE_METASTORE)
        sentry_host = cluster_context.get_instance(sentry.SENTRY)
        if sentry_host:
            sentry_mode = cluster_context._get_cluster_config_value(
                sentry.Sentry().SENTRY_STORAGE_MODE)
            ui_name = sentry.Sentry().ui_name
            sentry_version = cluster_context.get_chosen_service_version(
                ui_name)
            sentry_service = cluster_context. \
                _find_service_instance(ui_name, sentry_version)
            if sentry_service.supports(self, sentry_mode):
                cmd = 'sudo -u mapr hive -e "create role admin_role;' \
                      'grant all on server HS2 to role admin_role;' \
                      'grant role admin_role to group mapr;"'
                with instance.remote() as r:
                    LOG.debug("Creating hive role for sentry")
                    r.execute_command(cmd, raise_when_error=False)


class HiveV013(Hive):
    def __init__(self):
        super(HiveV013, self).__init__()
        self._version = '0.13'
        self._dependencies = [('mapr-hive', self.version)]


class HiveV10(Hive):
    def __init__(self):
        super(HiveV10, self).__init__()
        self._version = "1.0"
        self._dependencies = [("mapr-hive", self.version)]


class HiveV12(Hive):
    def __init__(self):
        super(HiveV12, self).__init__()
        self._version = "1.2"
        self._dependencies = [("mapr-hive", self.version)]
