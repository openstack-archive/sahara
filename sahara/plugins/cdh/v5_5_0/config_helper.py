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

from sahara.plugins.cdh import config_helper as c_h
from sahara.plugins import provisioning as p
from sahara.utils import files as f


class ConfigHelperV550(c_h.ConfigHelper):
    path_to_config = 'plugins/cdh/v5_5_0/resources/'

    CDH5_UBUNTU_REPO = (
        'deb [arch=amd64] http://archive.cloudera.com/cdh5'
        '/ubuntu/trusty/amd64/cdh trusty-cdh5.5.0 contrib'
        '\ndeb-src http://archive.cloudera.com/cdh5/ubuntu'
        '/trusty/amd64/cdh trusty-cdh5.5.0 contrib')

    DEFAULT_CDH5_UBUNTU_REPO_KEY_URL = (
        'http://archive.cloudera.com/cdh5/ubuntu'
        '/trusty/amd64/cdh/archive.key')

    CM5_UBUNTU_REPO = (
        'deb [arch=amd64] http://archive.cloudera.com/cm5'
        '/ubuntu/trusty/amd64/cm trusty-cm5.5.0 contrib'
        '\ndeb-src http://archive.cloudera.com/cm5/ubuntu'
        '/trusty/amd64/cm trusty-cm5.5.0 contrib')

    DEFAULT_CM5_UBUNTU_REPO_KEY_URL = (
        'http://archive.cloudera.com/cm5/ubuntu'
        '/trusty/amd64/cm/archive.key')

    CDH5_CENTOS_REPO = (
        '[cloudera-cdh5]'
        '\nname=Cloudera\'s Distribution for Hadoop, Version 5'
        '\nbaseurl=http://archive.cloudera.com/cdh5/redhat/6'
        '/x86_64/cdh/5.5.0/'
        '\ngpgkey = http://archive.cloudera.com/cdh5/redhat/6'
        '/x86_64/cdh/RPM-GPG-KEY-cloudera'
        '\ngpgcheck = 1')

    CM5_CENTOS_REPO = (
        '[cloudera-manager]'
        '\nname=Cloudera Manager'
        '\nbaseurl=http://archive.cloudera.com/cm5/redhat/6'
        '/x86_64/cm/5.5.0/'
        '\ngpgkey = http://archive.cloudera.com/cm5/redhat/6'
        '/x86_64/cm/RPM-GPG-KEY-cloudera'
        '\ngpgcheck = 1')

    KEY_TRUSTEE_UBUNTU_REPO_URL = (
        'http://archive.cloudera.com/navigator-'
        'keytrustee5/ubuntu/trusty/amd64/navigator-'
        'keytrustee/cloudera.list')

    DEFAULT_KEY_TRUSTEE_UBUNTU_REPO_KEY_URL = (
        'http://archive.cloudera.com/'
        'navigator-keytrustee5/ubuntu/'
        'trusty/amd64/navigator-keytrustee'
        '/archive.key')

    KEY_TRUSTEE_CENTOS_REPO_URL = (
        'http://archive.cloudera.com/navigator-'
        'keytrustee5/redhat/6/x86_64/navigator-'
        'keytrustee/navigator-keytrustee5.repo')

    DEFAULT_SWIFT_LIB_URL = (
        'https://repository.cloudera.com/artifactory/repo/org'
        '/apache/hadoop/hadoop-openstack/2.6.0-cdh5.5.0'
        '/hadoop-openstack-2.6.0-cdh5.5.0.jar')

    HIVE_SERVER2_SENTRY_SAFETY_VALVE = f.get_file_text(
        path_to_config + 'hive-server2-sentry-safety.xml')

    HIVE_METASTORE_SENTRY_SAFETY_VALVE = f.get_file_text(
        path_to_config + 'hive-metastore-sentry-safety.xml')

    SENTRY_IMPALA_CLIENT_SAFETY_VALVE = f.get_file_text(
        path_to_config + 'sentry-impala-client-safety.xml')

    _default_executor_classpath = ":".join(
        ['/usr/lib/hadoop/lib/jackson-core-asl-1.8.8.jar',
         '/usr/lib/hadoop-mapreduce/hadoop-openstack.jar'])

    EXECUTOR_EXTRA_CLASSPATH = p.Config(
        'Executor extra classpath', 'Spark', 'cluster', priority=2,
        default_value=_default_executor_classpath,
        description='Value for spark.executor.extraClassPath in '
                    'spark-defaults.conf (default: %s)'
                    % _default_executor_classpath)

    SWIFT_LIB_URL = p.Config(
        'Hadoop OpenStack library URL', 'general', 'cluster', priority=1,
        default_value=DEFAULT_SWIFT_LIB_URL,
        description=("Library that adds Swift support to CDH. The file"
                     " will be downloaded by VMs."))

    KMS_REPO_URL = p.Config(
        'KMS repo list URL', 'general', 'cluster', priority=1,
        default_value="")

    KMS_REPO_KEY_URL = p.Config(
        'KMS repo key URL (for debian-based only)', 'general',
        'cluster',
        priority=1, default_value="")

    REQUIRE_ANTI_AFFINITY = p.Config('Require Anti Affinity',
                                     'general', 'cluster',
                                     config_type='bool',
                                     priority=2,
                                     default_value=True)

    def __init__(self):
        super(ConfigHelperV550, self).__init__()
        self.priority_one_confs = self._load_json(
            self.path_to_config + 'priority-one-confs.json')
        self._init_all_ng_plugin_configs()

    def _get_cluster_plugin_configs(self):
        confs = super(ConfigHelperV550, self)._get_ng_plugin_configs()
        confs += [self.EXECUTOR_EXTRA_CLASSPATH,
                  self.KMS_REPO_URL,
                  self.KMS_REPO_KEY_URL,
                  self.REQUIRE_ANTI_AFFINITY]

        return confs

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
            'yarn-resourcemanager.json', 'YARN_GATEWAY', 'node')
        self.nodemanager_confs = self._load_and_init_configs(
            'yarn-nodemanager.json', 'RESOURCEMANAGER', 'node')
        self.jobhistory_confs = self._load_and_init_configs(
            'yarn-jobhistory.json', 'NODEMANAGER', 'node')
        self.yarn_gateway_conf = self._load_and_init_configs(
            'yarn-gateway.json', 'JOBHISTORY', 'node')
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
            'zookeeper-server.json', 'ZOOKEEPER', 'cluster')
        self.zookeeper_service_confs = self._load_and_init_configs(
            'zookeeper-service.json', 'ZOOKEEPER', 'node')
        self.hbase_confs = self._load_and_init_configs(
            'hbase-service.json', 'HBASE', 'cluster')
        self.master_confs = self._load_and_init_configs(
            'hbase-master.json', 'MASTER', 'node')
        self.regionserver_confs = self._load_and_init_configs(
            'hbase-regionserver.json', 'REGIONSERVER', 'node')
        self.flume_service_confs = self._load_and_init_configs(
            'flume-service.json', 'HDFS', 'cluster')
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

    def get_required_anti_affinity(self, cluster):
        return self._get_config_value(cluster, self.REQUIRE_ANTI_AFFINITY)

    def get_kms_key_url(self, cluster):
        return self._get_config_value(cluster, self.KMS_REPO_KEY_URL)
