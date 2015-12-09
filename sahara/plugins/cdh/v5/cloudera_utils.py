# Copyright (c) 2014 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sahara.i18n import _
from sahara.plugins.cdh import cloudera_utils as cu
from sahara.plugins.cdh.v5 import config_helper
from sahara.plugins.cdh.v5 import plugin_utils as pu
from sahara.plugins.cdh.v5 import validation
from sahara.swift import swift_helper
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import configs as s_cfg
from sahara.utils import xmlutils


HDFS_SERVICE_TYPE = 'HDFS'
YARN_SERVICE_TYPE = 'YARN'
OOZIE_SERVICE_TYPE = 'OOZIE'
HIVE_SERVICE_TYPE = 'HIVE'
HUE_SERVICE_TYPE = 'HUE'
SPARK_SERVICE_TYPE = 'SPARK_ON_YARN'
ZOOKEEPER_SERVICE_TYPE = 'ZOOKEEPER'
HBASE_SERVICE_TYPE = 'HBASE'

c_helper = config_helper.ConfigHelperV5()


class ClouderaUtilsV5(cu.ClouderaUtils):

    def __init__(self):
        cu.ClouderaUtils.__init__(self)
        self.pu = pu.PluginUtilsV5()
        self.validator = validation.ValidatorV5

    @cu.cloudera_cmd
    def format_namenode(self, hdfs_service):
        for nn in hdfs_service.get_roles_by_type('NAMENODE'):
            yield hdfs_service.format_hdfs(nn.name)[0]

    @cu.cloudera_cmd
    def create_hdfs_tmp(self, hdfs_service):
        yield hdfs_service.create_hdfs_tmp()

    @cu.cloudera_cmd
    def create_yarn_job_history_dir(self, yarn_service):
        yield yarn_service.create_yarn_job_history_dir()

    @cu.cloudera_cmd
    def create_oozie_db(self, oozie_service):
        yield oozie_service.create_oozie_db()

    @cu.cloudera_cmd
    def install_oozie_sharelib(self, oozie_service):
        yield oozie_service.install_oozie_sharelib()

    @cu.cloudera_cmd
    def create_hive_metastore_db(self, hive_service):
        yield hive_service.create_hive_metastore_tables()

    @cu.cloudera_cmd
    def create_hive_dirs(self, hive_service):
        yield hive_service.create_hive_userdir()
        yield hive_service.create_hive_warehouse()

    @cu.cloudera_cmd
    def create_hbase_root(self, hbase_service):
        yield hbase_service.create_hbase_root()

    @cpo.event_wrapper(True, step=_("Create services"), param=('cluster', 1))
    def create_services(self, cluster):
        api = self.get_api_client(cluster)

        fullversion = ('5.0.0' if cluster.hadoop_version == '5'
                       else cluster.hadoop_version)
        cm_cluster = api.create_cluster(cluster.name,
                                        fullVersion=fullversion)

        if len(self.pu.get_zookeepers(cluster)) > 0:
            cm_cluster.create_service(self.ZOOKEEPER_SERVICE_NAME,
                                      ZOOKEEPER_SERVICE_TYPE)
        cm_cluster.create_service(self.HDFS_SERVICE_NAME, HDFS_SERVICE_TYPE)
        cm_cluster.create_service(self.YARN_SERVICE_NAME, YARN_SERVICE_TYPE)
        cm_cluster.create_service(self.OOZIE_SERVICE_NAME, OOZIE_SERVICE_TYPE)
        if self.pu.get_hive_metastore(cluster):
            cm_cluster.create_service(self.HIVE_SERVICE_NAME,
                                      HIVE_SERVICE_TYPE)
        if self.pu.get_hue(cluster):
            cm_cluster.create_service(self.HUE_SERVICE_NAME, HUE_SERVICE_TYPE)
        if self.pu.get_spark_historyserver(cluster):
            cm_cluster.create_service(self.SPARK_SERVICE_NAME,
                                      SPARK_SERVICE_TYPE)
        if self.pu.get_hbase_master(cluster):
            cm_cluster.create_service(self.HBASE_SERVICE_NAME,
                                      HBASE_SERVICE_TYPE)

    def await_agents(self, cluster, instances):
        self._await_agents(cluster, instances, c_helper.AWAIT_AGENTS_TIMEOUT)

    @cpo.event_wrapper(
        True, step=_("Configure services"), param=('cluster', 1))
    def configure_services(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)

        if len(self.pu.get_zookeepers(cluster)) > 0:
            zookeeper = cm_cluster.get_service(self.ZOOKEEPER_SERVICE_NAME)
            zookeeper.update_config(self._get_configs(ZOOKEEPER_SERVICE_TYPE,
                                    cluster=cluster))

        hdfs = cm_cluster.get_service(self.HDFS_SERVICE_NAME)
        hdfs.update_config(self._get_configs(HDFS_SERVICE_TYPE,
                                             cluster=cluster))

        yarn = cm_cluster.get_service(self.YARN_SERVICE_NAME)
        yarn.update_config(self._get_configs(YARN_SERVICE_TYPE,
                                             cluster=cluster))

        oozie = cm_cluster.get_service(self.OOZIE_SERVICE_NAME)
        oozie.update_config(self._get_configs(OOZIE_SERVICE_TYPE,
                                              cluster=cluster))

        if self.pu.get_hive_metastore(cluster):
            hive = cm_cluster.get_service(self.HIVE_SERVICE_NAME)
            hive.update_config(self._get_configs(HIVE_SERVICE_TYPE,
                                                 cluster=cluster))

        if self.pu.get_hue(cluster):
            hue = cm_cluster.get_service(self.HUE_SERVICE_NAME)
            hue.update_config(self._get_configs(HUE_SERVICE_TYPE,
                                                cluster=cluster))

        if self.pu.get_spark_historyserver(cluster):
            spark = cm_cluster.get_service(self.SPARK_SERVICE_NAME)
            spark.update_config(self._get_configs(SPARK_SERVICE_TYPE,
                                                  cluster=cluster))

        if self.pu.get_hbase_master(cluster):
            hbase = cm_cluster.get_service(self.HBASE_SERVICE_NAME)
            hbase.update_config(self._get_configs(HBASE_SERVICE_TYPE,
                                                  cluster=cluster))

    def _get_configs(self, service, cluster=None, instance=None):
        def get_hadoop_dirs(mount_points, suffix):
            return ','.join([x + suffix for x in mount_points])

        all_confs = {}
        if cluster:
            zk_count = self.validator._get_inst_count(cluster,
                                                      'ZOOKEEPER_SERVER')
            core_site_safety_valve = ''
            if self.pu.c_helper.is_swift_enabled(cluster):
                configs = swift_helper.get_swift_configs()
                confs = {c['name']: c['value'] for c in configs}
                core_site_safety_valve = xmlutils.create_elements_xml(confs)
            all_confs = {
                'HDFS': {
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else '',
                    'core_site_safety_valve': core_site_safety_valve
                },
                'HIVE': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME,
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'OOZIE': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME,
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'YARN': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'HUE': {
                    'hive_service': self.HIVE_SERVICE_NAME,
                    'oozie_service': self.OOZIE_SERVICE_NAME,
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'SPARK_ON_YARN': {
                    'yarn_service': self.YARN_SERVICE_NAME
                },
                'HBASE': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'zookeeper_service': self.ZOOKEEPER_SERVICE_NAME
                }
            }
            hive_confs = {
                'HIVE': {
                    'hive_metastore_database_type': 'postgresql',
                    'hive_metastore_database_host':
                        self.pu.get_manager(cluster).internal_ip,
                    'hive_metastore_database_port': '7432',
                    'hive_metastore_database_password':
                        self.pu.db_helper.get_hive_db_password(cluster)
                }
            }
            hue_confs = {
                'HUE': {
                    'hue_webhdfs':
                        self.pu.get_role_name(self.pu.get_namenode(cluster),
                                              'NAMENODE')
                }
            }

            all_confs = s_cfg.merge_configs(all_confs, hue_confs)
            all_confs = s_cfg.merge_configs(all_confs, hive_confs)
            all_confs = s_cfg.merge_configs(all_confs, cluster.cluster_configs)

        if instance:
            paths = instance.storage_paths()

            instance_default_confs = {
                'NAMENODE': {
                    'dfs_name_dir_list': get_hadoop_dirs(paths, '/fs/nn')
                },
                'SECONDARYNAMENODE': {
                    'fs_checkpoint_dir_list':
                        get_hadoop_dirs(paths, '/fs/snn')
                },
                'DATANODE': {
                    'dfs_data_dir_list': get_hadoop_dirs(paths, '/fs/dn'),
                    'dfs_datanode_data_dir_perm': 755,
                    'dfs_datanode_handler_count': 30
                },
                'NODEMANAGER': {
                    'yarn_nodemanager_local_dirs':
                        get_hadoop_dirs(paths, '/yarn/local')
                },
                'SERVER': {
                    'maxSessionTimeout': 60000
                }
            }

            ng_user_confs = self.pu.convert_process_configs(
                instance.node_group.node_configs)
            all_confs = s_cfg.merge_configs(all_confs, ng_user_confs)
            all_confs = s_cfg.merge_configs(all_confs, instance_default_confs)

        return all_confs.get(service, {})
