# Copyright (c) 2015 Intel Corporation
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
from sahara.plugins.cdh.v5_5_0 import config_helper
from sahara.plugins.cdh.v5_5_0 import plugin_utils as pu
from sahara.plugins.cdh.v5_5_0 import validation
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
FLUME_SERVICE_TYPE = 'FLUME'
SENTRY_SERVICE_TYPE = 'SENTRY'
SOLR_SERVICE_TYPE = 'SOLR'
SQOOP_SERVICE_TYPE = 'SQOOP'
KS_INDEXER_SERVICE_TYPE = 'KS_INDEXER'
IMPALA_SERVICE_TYPE = 'IMPALA'
KMS_SERVICE_TYPE = 'KMS'

c_helper = config_helper.ConfigHelperV550()


class ClouderaUtilsV550(cu.ClouderaUtils):
    FLUME_SERVICE_NAME = 'flume01'
    SOLR_SERVICE_NAME = 'solr01'
    SQOOP_SERVICE_NAME = 'sqoop01'
    KS_INDEXER_SERVICE_NAME = 'ks_indexer01'
    IMPALA_SERVICE_NAME = 'impala01'
    SENTRY_SERVICE_NAME = 'sentry01'
    KMS_SERVICE_NAME = 'kms01'
    CM_API_VERSION = 8
    NAME_SERVICE = 'nameservice01'

    def __init__(self):
        cu.ClouderaUtils.__init__(self)
        self.pu = pu.PluginUtilsV550()
        self.validator = validation.ValidatorV550

    def get_service_by_role(self, role, cluster=None, instance=None):
        cm_cluster = None
        if cluster:
            cm_cluster = self.get_cloudera_cluster(cluster)
        elif instance:
            cm_cluster = self.get_cloudera_cluster(instance.cluster)
        else:
            raise ValueError(_("'cluster' or 'instance' argument missed"))

        if role in ['AGENT']:
            return cm_cluster.get_service(self.FLUME_SERVICE_NAME)
        elif role in ['SENTRY_SERVER']:
            return cm_cluster.get_service(self.SENTRY_SERVICE_NAME)
        elif role in ['SQOOP_SERVER']:
            return cm_cluster.get_service(self.SQOOP_SERVICE_NAME)
        elif role in ['SOLR_SERVER']:
            return cm_cluster.get_service(self.SOLR_SERVICE_NAME)
        elif role in ['HBASE_INDEXER']:
            return cm_cluster.get_service(self.KS_INDEXER_SERVICE_NAME)
        elif role in ['CATALOGSERVER', 'STATESTORE', 'IMPALAD', 'LLAMA']:
            return cm_cluster.get_service(self.IMPALA_SERVICE_NAME)
        elif role in ['KMS']:
            return cm_cluster.get_service(self.KMS_SERVICE_NAME)
        elif role in ['JOURNALNODE']:
            return cm_cluster.get_service(self.HDFS_SERVICE_NAME)
        elif role in ['YARN_STANDBYRM']:
            return cm_cluster.get_service(self.YARN_SERVICE_NAME)
        else:
            return super(ClouderaUtilsV550, self).get_service_by_role(
                role, cluster, instance)

    @cpo.event_wrapper(
        True, step=_("First run cluster"), param=('cluster', 1))
    @cu.cloudera_cmd
    def first_run(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)
        yield cm_cluster.first_run()

    @cpo.event_wrapper(True, step=_("Create services"), param=('cluster', 1))
    def create_services(self, cluster):
        api = self.get_api_client(cluster)
        cm_cluster = api.create_cluster(cluster.name,
                                        fullVersion=cluster.hadoop_version)

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
        if len(self.pu.get_flumes(cluster)) > 0:
            cm_cluster.create_service(self.FLUME_SERVICE_NAME,
                                      FLUME_SERVICE_TYPE)
        if self.pu.get_sentry(cluster):
            cm_cluster.create_service(self.SENTRY_SERVICE_NAME,
                                      SENTRY_SERVICE_TYPE)
        if len(self.pu.get_solrs(cluster)) > 0:
            cm_cluster.create_service(self.SOLR_SERVICE_NAME,
                                      SOLR_SERVICE_TYPE)
        if self.pu.get_sqoop(cluster):
            cm_cluster.create_service(self.SQOOP_SERVICE_NAME,
                                      SQOOP_SERVICE_TYPE)
        if len(self.pu.get_hbase_indexers(cluster)) > 0:
            cm_cluster.create_service(self.KS_INDEXER_SERVICE_NAME,
                                      KS_INDEXER_SERVICE_TYPE)
        if self.pu.get_catalogserver(cluster):
            cm_cluster.create_service(self.IMPALA_SERVICE_NAME,
                                      IMPALA_SERVICE_TYPE)
        if self.pu.get_kms(cluster):
            cm_cluster.create_service(self.KMS_SERVICE_NAME,
                                      KMS_SERVICE_TYPE)

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

        if len(self.pu.get_flumes(cluster)) > 0:
            flume = cm_cluster.get_service(self.FLUME_SERVICE_NAME)
            flume.update_config(self._get_configs(FLUME_SERVICE_TYPE,
                                                  cluster=cluster))

        if self.pu.get_sentry(cluster):
            sentry = cm_cluster.get_service(self.SENTRY_SERVICE_NAME)
            sentry.update_config(self._get_configs(SENTRY_SERVICE_TYPE,
                                                   cluster=cluster))

        if len(self.pu.get_solrs(cluster)) > 0:
            solr = cm_cluster.get_service(self.SOLR_SERVICE_NAME)
            solr.update_config(self._get_configs(SOLR_SERVICE_TYPE,
                                                 cluster=cluster))

        if self.pu.get_sqoop(cluster):
            sqoop = cm_cluster.get_service(self.SQOOP_SERVICE_NAME)
            sqoop.update_config(self._get_configs(SQOOP_SERVICE_TYPE,
                                                  cluster=cluster))

        if len(self.pu.get_hbase_indexers(cluster)) > 0:
            ks_indexer = cm_cluster.get_service(self.KS_INDEXER_SERVICE_NAME)
            ks_indexer.update_config(
                self._get_configs(KS_INDEXER_SERVICE_TYPE, cluster=cluster))

        if self.pu.get_catalogserver(cluster):
            impala = cm_cluster.get_service(self.IMPALA_SERVICE_NAME)
            impala.update_config(self._get_configs(IMPALA_SERVICE_TYPE,
                                                   cluster=cluster))

        if self.pu.get_kms(cluster):
            kms = cm_cluster.get_service(self.KMS_SERVICE_NAME)
            kms.update_config(self._get_configs(KMS_SERVICE_TYPE,
                                                cluster=cluster))

    def _get_configs(self, service, cluster=None, instance=None):
        def get_hadoop_dirs(mount_points, suffix):
            return ','.join([x + suffix for x in mount_points])

        all_confs = {}
        if cluster:
            zk_count = self.validator._get_inst_count(cluster,
                                                      'ZOOKEEPER_SERVER')
            hbm_count = self.validator._get_inst_count(cluster, 'HBASE_MASTER')
            snt_count = self.validator._get_inst_count(cluster,
                                                       'SENTRY_SERVER')
            ks_count =\
                self.validator._get_inst_count(cluster,
                                               'KEY_VALUE_STORE_INDEXER')
            kms_count = self.validator._get_inst_count(cluster, 'KMS')
            imp_count =\
                self.validator._get_inst_count(cluster,
                                               'IMPALA_CATALOGSERVER')
            hive_count = self.validator._get_inst_count(cluster,
                                                        'HIVE_METASTORE')
            slr_count = self.validator._get_inst_count(cluster, 'SOLR_SERVER')
            sqp_count = self.validator._get_inst_count(cluster, 'SQOOP_SERVER')
            core_site_safety_valve = ''
            if self.pu.c_helper.is_swift_enabled(cluster):
                configs = swift_helper.get_swift_configs()
                confs = {c['name']: c['value'] for c in configs}
                core_site_safety_valve = xmlutils.create_elements_xml(confs)
            all_confs = {
                'HDFS': {
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else '',
                    'dfs_block_local_path_access_user':
                        'impala' if imp_count else '',
                    'kms_service': self.KMS_SERVICE_NAME if kms_count else '',
                    'core_site_safety_valve': core_site_safety_valve
                },
                'HIVE': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME,
                    'sentry_service':
                        self.SENTRY_SERVICE_NAME if snt_count else '',
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'OOZIE': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME,
                    'hive_service':
                        self.HIVE_SERVICE_NAME if hive_count else '',
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
                    'sentry_service':
                        self.SENTRY_SERVICE_NAME if snt_count else '',
                    'solr_service':
                        self.SOLR_SERVICE_NAME if slr_count else '',
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else '',
                    'hbase_service':
                        self.HBASE_SERVICE_NAME if hbm_count else '',
                    'impala_service':
                        self.IMPALA_SERVICE_NAME if imp_count else '',
                    'sqoop_service':
                        self.SQOOP_SERVICE_NAME if sqp_count else ''
                },
                'SPARK_ON_YARN': {
                    'yarn_service': self.YARN_SERVICE_NAME
                },
                'HBASE': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'zookeeper_service': self.ZOOKEEPER_SERVICE_NAME,
                    'hbase_enable_indexing': 'true' if ks_count else 'false',
                    'hbase_enable_replication':
                        'true' if ks_count else 'false'
                },
                'FLUME': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'solr_service':
                        self.SOLR_SERVICE_NAME if slr_count else '',
                    'hbase_service':
                        self.HBASE_SERVICE_NAME if hbm_count else ''
                },
                'SENTRY': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'sentry_server_config_safety_valve': (
                        c_helper.SENTRY_IMPALA_CLIENT_SAFETY_VALVE
                        if imp_count else '')
                },
                'SOLR': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'zookeeper_service': self.ZOOKEEPER_SERVICE_NAME
                },
                'SQOOP': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME
                },
                'KS_INDEXER': {
                    'hbase_service': self.HBASE_SERVICE_NAME,
                    'solr_service': self.SOLR_SERVICE_NAME
                },
                'IMPALA': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'hbase_service':
                        self.HBASE_SERVICE_NAME if hbm_count else '',
                    'hive_service': self.HIVE_SERVICE_NAME,
                    'sentry_service':
                        self.SENTRY_SERVICE_NAME if snt_count else '',
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
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
                    'hue_webhdfs': self.pu.get_role_name(
                        self.pu.get_namenode(cluster), 'NAMENODE')
                }
            }
            sentry_confs = {
                'SENTRY': {
                    'sentry_server_database_type': 'postgresql',
                    'sentry_server_database_host':
                        self.pu.get_manager(cluster).internal_ip,
                    'sentry_server_database_port': '7432',
                    'sentry_server_database_password':
                        self.pu.db_helper.get_sentry_db_password(cluster)
                }
            }

            all_confs = s_cfg.merge_configs(all_confs, hue_confs)
            all_confs = s_cfg.merge_configs(all_confs, hive_confs)
            all_confs = s_cfg.merge_configs(all_confs, sentry_confs)
            all_confs = s_cfg.merge_configs(all_confs, cluster.cluster_configs)

        if instance:
            snt_count = self.validator._get_inst_count(instance.cluster,
                                                       'SENTRY_SERVER')
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
                },
                'HIVESERVER2': {
                    'hiveserver2_enable_impersonation':
                        'false' if snt_count else 'true',
                    'hive_hs2_config_safety_valve': (
                        c_helper.HIVE_SERVER2_SENTRY_SAFETY_VALVE
                        if snt_count else '')
                },
                'HIVEMETASTORE': {
                    'hive_metastore_config_safety_valve': (
                        c_helper.HIVE_METASTORE_SENTRY_SAFETY_VALVE
                        if snt_count else '')
                }
            }

            ng_user_confs = self.pu.convert_process_configs(
                instance.node_group.node_configs)
            all_confs = s_cfg.merge_configs(all_confs, ng_user_confs)
            all_confs = s_cfg.merge_configs(all_confs, instance_default_confs)

        return all_confs.get(service, {})

    @cpo.event_wrapper(
        True, step=_("Enable NameNode HA"), param=('cluster', 1))
    @cu.cloudera_cmd
    def enable_namenode_ha(self, cluster):
        standby_nn = self.pu.get_secondarynamenode(cluster)
        standby_nn_host_name = standby_nn.fqdn()
        jns = self.pu.get_jns(cluster)
        jn_list = []
        for index, jn in enumerate(jns):
            jn_host_name = jn.fqdn()
            jn_list.append({'jnHostId': jn_host_name,
                            'jnName': 'JN%i' % index,
                            'jnEditsDir': '/dfs/jn'
                            })
        cm_cluster = self.get_cloudera_cluster(cluster)
        hdfs = cm_cluster.get_service(self.HDFS_SERVICE_NAME)
        nn = hdfs.get_roles_by_type('NAMENODE')[0]

        yield hdfs.enable_nn_ha(active_name=nn.name,
                                standby_host_id=standby_nn_host_name,
                                nameservice=self.NAME_SERVICE, jns=jn_list
                                )

    @cpo.event_wrapper(
        True, step=_("Enable ResourceManager HA"), param=('cluster', 1))
    @cu.cloudera_cmd
    def enable_resourcemanager_ha(self, cluster):
        new_rm = self.pu.get_stdb_rm(cluster)
        new_rm_host_name = new_rm.fqdn()
        cm_cluster = self.get_cloudera_cluster(cluster)
        yarn = cm_cluster.get_service(self.YARN_SERVICE_NAME)
        yield yarn.enable_rm_ha(new_rm_host_id=new_rm_host_name)
