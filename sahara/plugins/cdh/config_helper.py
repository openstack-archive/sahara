# Copyright (c) 2016 Mirantis Inc.
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

from oslo_serialization import jsonutils as json

from sahara.plugins import provisioning as p
from sahara.utils import files as f


class ConfigHelper(object):
    path_to_config = ''

    CDH5_REPO_URL = p.Config(
        'CDH5 repo list URL', 'general', 'cluster', priority=1,
        default_value="")

    CDH5_REPO_KEY_URL = p.Config(
        'CDH5 repo key URL (for debian-based only)', 'general', 'cluster',
        priority=1, default_value="")

    CM5_REPO_URL = p.Config(
        'CM5 repo list URL', 'general', 'cluster', priority=1,
        default_value="")

    CM5_REPO_KEY_URL = p.Config(
        'CM5 repo key URL (for debian-based only)', 'general', 'cluster',
        priority=1, default_value="")

    ENABLE_HBASE_COMMON_LIB = p.Config(
        'Enable HBase Common Lib', 'general', 'cluster', config_type='bool',
        priority=1, default_value=True)

    ENABLE_SWIFT = p.Config(
        'Enable Swift', 'general', 'cluster',
        config_type='bool', priority=1, default_value=True)

    DEFAULT_SWIFT_LIB_URL = (
        'https://repository.cloudera.com/artifactory/repo/org'
        '/apache/hadoop/hadoop-openstack/2.6.0-cdh5.5.0'
        '/hadoop-openstack-2.6.0-cdh5.5.0.jar')

    SWIFT_LIB_URL = p.Config(
        'Hadoop OpenStack library URL', 'general', 'cluster', priority=1,
        default_value=DEFAULT_SWIFT_LIB_URL,
        description=("Library that adds Swift support to CDH. The file"
                     " will be downloaded by VMs."))

    DEFAULT_EXTJS_LIB_URL = (
        'https://tarballs.openstack.org/sahara-extra/dist/common-artifacts/'
        'ext-2.2.zip')

    EXTJS_LIB_URL = p.Config(
        "ExtJS library URL", 'general', 'cluster', priority=1,
        default_value=DEFAULT_EXTJS_LIB_URL,
        description=("Ext 2.2 library is required for Oozie Web Console. "
                     "The file will be downloaded by VMs with oozie."))

    _default_executor_classpath = ":".join(
        ['/usr/lib/hadoop/lib/jackson-core-asl-1.8.8.jar',
         '/usr/lib/hadoop-mapreduce/hadoop-openstack.jar'])

    EXECUTOR_EXTRA_CLASSPATH = p.Config(
        'Executor extra classpath', 'Spark', 'cluster', priority=2,
        default_value=_default_executor_classpath,
        description='Value for spark.executor.extraClassPath in '
                    'spark-defaults.conf (default: %s)'
                    % _default_executor_classpath)

    KMS_REPO_URL = p.Config(
        'KMS repo list URL', 'general', 'cluster', priority=1,
        default_value="")

    KMS_REPO_KEY_URL = p.Config(
        'KMS repo key URL (for debian-based only)', 'general',
        'cluster',
        priority=1, default_value="")

    REQUIRE_ANTI_AFFINITY = p.Config(
        'Require Anti Affinity', 'general', 'cluster',
        config_type='bool', priority=2, default_value=True)

    AWAIT_AGENTS_TIMEOUT = p.Config(
        'Await Cloudera agents timeout', 'general', 'cluster',
        config_type='int', priority=1, default_value=300, is_optional=True,
        description="Timeout for Cloudera agents connecting to"
                    " Cloudera Manager, in seconds")

    AWAIT_MANAGER_STARTING_TIMEOUT = p.Config(
        'Timeout for Cloudera Manager starting', 'general', 'cluster',
        config_type='int', priority=1, default_value=300, is_optional=True,
        description='Timeout for Cloudera Manager starting, in seconds')

    def __new__(cls):
        # make it a singleton
        if not hasattr(cls, '_instance'):
            cls._instance = super(ConfigHelper, cls).__new__(cls)
            setattr(cls, '__init__', cls.decorate_init(cls.__init__))
        return cls._instance

    @classmethod
    def decorate_init(cls, f):
        """decorate __init__ to prevent multiple calling."""
        def wrap(*args, **kwargs):
            if not hasattr(cls, '_init'):
                f(*args, **kwargs)
                cls._init = True
        return wrap

    def __init__(self):
        self.ng_plugin_configs = []
        self.priority_one_confs = {}

    def _load_json(self, path_to_file):
        data = f.get_file_text(path_to_file)
        return json.loads(data)

    def _init_ng_configs(self, confs, app_target, scope):
        prepare_value = lambda x: x.replace('\n', ' ') if x else ""
        cfgs = []
        for cfg in confs:
            priority = 1 if cfg['name'] in self.priority_one_confs else 2
            c = p.Config(cfg['name'], app_target, scope, priority=priority,
                         default_value=prepare_value(cfg['value']),
                         description=cfg['desc'], is_optional=True)
            cfgs.append(c)

        return cfgs

    def _init_all_ng_plugin_configs(self):
        self.hdfs_confs = self._load_and_init_configs(
            'hdfs-service.json', 'HDFS', 'cluster')
        self.namenode_confs = self._load_and_init_configs(
            'hdfs-namenode.json', 'NAMENODE', 'node')
        self.datanode_confs = self._load_and_init_configs(
            'hdfs-datanode.json', 'DATANODE', 'node')
        self.secnamenode_confs = self._load_and_init_configs(
            'hdfs-secondarynamenode.json', 'SECONDARYNAMENODE', 'node')
        self.hdfs_gateway_confs = self._load_and_init_configs(
            'hdfs-gateway.json', 'HDFS_GATEWAY', 'node')
        self.journalnode_confs = self._load_and_init_configs(
            'hdfs-journalnode.json', 'JOURNALNODE', 'node')

        self.yarn_confs = self._load_and_init_configs(
            'yarn-service.json', 'YARN', 'cluster')
        self.resourcemanager_confs = self._load_and_init_configs(
            'yarn-resourcemanager.json', 'RESOURCEMANAGER', 'node')
        self.nodemanager_confs = self._load_and_init_configs(
            'yarn-nodemanager.json', 'NODEMANAGER', 'node')
        self.jobhistory_confs = self._load_and_init_configs(
            'yarn-jobhistory.json', 'JOBHISTORY', 'node')
        self.yarn_gateway_conf = self._load_and_init_configs(
            'yarn-gateway.json', 'YARN_GATEWAY', 'node')

        self.oozie_service_confs = self._load_and_init_configs(
            'oozie-service.json', 'OOZIE', 'cluster')
        self.oozie_role_confs = self._load_and_init_configs(
            'oozie-oozie_server.json', 'OOZIE', 'node')

        self.hive_service_confs = self._load_and_init_configs(
            'hive-service.json', 'HIVE', 'cluster')
        self.hive_metastore_confs = self._load_and_init_configs(
            'hive-hivemetastore.json', 'HIVEMETASTORE', 'node')
        self.hive_hiveserver_confs = self._load_and_init_configs(
            'hive-hiveserver2.json', 'HIVESERVER', 'node')
        self.hive_webhcat_confs = self._load_and_init_configs(
            'hive-webhcat.json', 'WEBHCAT', 'node')

        self.hue_service_confs = self._load_and_init_configs(
            'hue-service.json', 'HUE', 'cluster')
        self.hue_role_confs = self._load_and_init_configs(
            'hue-hue_server.json', 'HUE', 'node')

        self.spark_service_confs = self._load_and_init_configs(
            'spark-service.json', 'SPARK_ON_YARN', 'cluster')
        self.spark_role_confs = self._load_and_init_configs(
            'spark-spark_yarn_history_server.json', 'SPARK_ON_YARN', 'node')

        self.zookeeper_server_confs = self._load_and_init_configs(
            'zookeeper-service.json', 'ZOOKEEPER', 'cluster')
        self.zookeeper_service_confs = self._load_and_init_configs(
            'zookeeper-server.json', 'ZOOKEEPER', 'node')

        self.hbase_confs = self._load_and_init_configs(
            'hbase-service.json', 'HBASE', 'cluster')
        self.master_confs = self._load_and_init_configs(
            'hbase-master.json', 'MASTER', 'node')
        self.regionserver_confs = self._load_and_init_configs(
            'hbase-regionserver.json', 'REGIONSERVER', 'node')

        self.flume_service_confs = self._load_and_init_configs(
            'flume-service.json', 'FLUME', 'cluster')
        self.flume_agent_confs = self._load_and_init_configs(
            'flume-agent.json', 'FLUME', 'node')

        self.sentry_service_confs = self._load_and_init_configs(
            'sentry-service.json', 'SENTRY', 'cluster')
        self.sentry_server_confs = self._load_and_init_configs(
            'sentry-sentry_server.json', 'SENTRY', 'node')

        self.solr_service_confs = self._load_and_init_configs(
            'solr-service.json', 'SOLR', 'cluster')
        self.solr_server_confs = self._load_and_init_configs(
            'solr-solr_server.json', 'SOLR', 'node')

        self.sqoop_service_confs = self._load_and_init_configs(
            'sqoop-service.json', 'SQOOP', 'cluster')
        self.sqoop_server_confs = self._load_and_init_configs(
            'sqoop-sqoop_server.json', 'SQOOP', 'node')

        self.ks_indexer_service_confs = self._load_and_init_configs(
            'ks_indexer-service.json', 'KS_INDEXER', 'cluster')
        self.ks_indexer_role_confs = self._load_and_init_configs(
            'ks_indexer-hbase_indexer.json', 'KS_INDEXER', 'node')

        self.impala_service_confs = self._load_and_init_configs(
            'impala-service.json', 'IMPALA', 'cluster')
        self.impala_catalogserver_confs = self._load_and_init_configs(
            'impala-catalogserver.json', 'CATALOGSERVER', 'node')
        self.impala_impalad_confs = self._load_and_init_configs(
            'impala-impalad.json', 'IMPALAD', 'node')
        self.impala_statestore_confs = self._load_and_init_configs(
            'impala-statestore.json', 'STATESTORE', 'node')

        self.kms_service_confs = self._load_and_init_configs(
            'kms-service.json', 'KMS', 'cluster')
        self.kms_kms_confs = self._load_and_init_configs(
            'kms-kms.json', 'KMS', 'node')

        self.kafka_service = self._load_and_init_configs(
            'kafka-service.json', 'KAFKA', 'cluster')
        self.kafka_kafka_broker = self._load_and_init_configs(
            'kafka-kafka_broker.json', 'KAFKA', 'node')
        self.kafka_kafka_mirror_maker = self._load_and_init_configs(
            'kafka-kafka_mirror_maker.json', 'KAFKA', 'node')

    def _load_and_init_configs(self, filename, app_target, scope):
        confs = self._load_json(self.path_to_config + filename)
        cfgs = self._init_ng_configs(confs, app_target, scope)
        self.ng_plugin_configs += cfgs

        return cfgs

    def _get_ng_plugin_configs(self):
        return self.ng_plugin_configs

    def _get_cluster_plugin_configs(self):
        return [self.CDH5_REPO_URL, self.CDH5_REPO_KEY_URL, self.CM5_REPO_URL,
                self.CM5_REPO_KEY_URL, self.ENABLE_SWIFT, self.SWIFT_LIB_URL,
                self.ENABLE_HBASE_COMMON_LIB, self.EXTJS_LIB_URL,
                self.AWAIT_MANAGER_STARTING_TIMEOUT, self.AWAIT_AGENTS_TIMEOUT,
                self.EXECUTOR_EXTRA_CLASSPATH, self.KMS_REPO_URL,
                self.KMS_REPO_KEY_URL, self.REQUIRE_ANTI_AFFINITY]

    def get_plugin_configs(self):
        cluster_wide = self._get_cluster_plugin_configs()
        ng_wide = self._get_ng_plugin_configs()
        return cluster_wide + ng_wide

    def _get_config_value(self, cluster, key):
        return cluster.cluster_configs.get(
            'general', {}).get(key.name, key.default_value)

    def get_cdh5_repo_url(self, cluster):
        return self._get_config_value(cluster, self.CDH5_REPO_URL)

    def get_cdh5_key_url(self, cluster):
        return self._get_config_value(cluster, self.CDH5_REPO_KEY_URL)

    def get_cm5_repo_url(self, cluster):
        return self._get_config_value(cluster, self.CM5_REPO_URL)

    def get_cm5_key_url(self, cluster):
        return self._get_config_value(cluster, self.CM5_REPO_KEY_URL)

    def is_swift_enabled(self, cluster):
        return self._get_config_value(cluster, self.ENABLE_SWIFT)

    def is_hbase_common_lib_enabled(self, cluster):
        return self._get_config_value(cluster,
                                      self.ENABLE_HBASE_COMMON_LIB)

    def get_swift_lib_url(self, cluster):
        return self._get_config_value(cluster, self.SWIFT_LIB_URL)

    def get_extjs_lib_url(self, cluster):
        return self._get_config_value(cluster, self.EXTJS_LIB_URL)

    def get_kms_key_url(self, cluster):
        return self._get_config_value(cluster, self.KMS_REPO_KEY_URL)

    def get_required_anti_affinity(self, cluster):
        return self._get_config_value(cluster, self.REQUIRE_ANTI_AFFINITY)
