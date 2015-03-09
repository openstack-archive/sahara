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

import json

from sahara.plugins import provisioning as p
from sahara.utils import files as f

CDH5_UBUNTU_REPO = ('deb [arch=amd64] http://archive.cloudera.com/cdh5'
                    '/ubuntu/precise/amd64/cdh precise-cdh5.3.0 contrib'
                    '\ndeb-src http://archive.cloudera.com/cdh5/ubuntu'
                    '/precise/amd64/cdh precise-cdh5.3.0 contrib')

DEFAULT_CDH5_UBUNTU_REPO_KEY_URL = ('http://archive.cloudera.com/cdh5/ubuntu'
                                    '/precise/amd64/cdh/archive.key')

CM5_UBUNTU_REPO = ('deb [arch=amd64] http://archive.cloudera.com/cm5'
                   '/ubuntu/precise/amd64/cm precise-cm5.3.0 contrib'
                   '\ndeb-src http://archive.cloudera.com/cm5/ubuntu'
                   '/precise/amd64/cm precise-cm5.3.0 contrib')

DEFAULT_CM5_UBUNTU_REPO_KEY_URL = ('http://archive.cloudera.com/cm5/ubuntu'
                                   '/precise/amd64/cm/archive.key')

CDH5_CENTOS_REPO = ('[cloudera-cdh5]'
                    '\nname=Cloudera\'s Distribution for Hadoop, Version 5'
                    '\nbaseurl=http://archive.cloudera.com/cdh5/redhat/6'
                    '/x86_64/cdh/5.3.0/'
                    '\ngpgkey = http://archive.cloudera.com/cdh5/redhat/6'
                    '/x86_64/cdh/RPM-GPG-KEY-cloudera'
                    '\ngpgcheck = 1')

CM5_CENTOS_REPO = ('[cloudera-manager]'
                   '\nname=Cloudera Manager'
                   '\nbaseurl=http://archive.cloudera.com/cm5/redhat/6'
                   '/x86_64/cm/5.3.0/'
                   '\ngpgkey = http://archive.cloudera.com/cm5/redhat/6'
                   '/x86_64/cm/RPM-GPG-KEY-cloudera'
                   '\ngpgcheck = 1')

DEFAULT_SWIFT_LIB_URL = ('https://repository.cloudera.com/artifactory/repo/org'
                         '/apache/hadoop/hadoop-openstack/2.5.0-cdh5.3.0'
                         '/hadoop-openstack-2.5.0-cdh5.3.0.jar')
DEFAULT_EXTJS_LIB_URL = 'http://extjs.com/deploy/ext-2.2.zip'

HIVE_SERVER2_SENTRY_SAFETY_VALVE = (
    '<property>'
    '\n   <name>hive.security.authorization.task.factory</name>'
    '\n   <value>org.apache.sentry.binding.hive.SentryHiveAuthorizationTask'
    'FactoryImpl</value>'
    '\n</property>'
    '\n<property>'
    '\n   <name>hive.server2.session.hook</name>'
    '\n   <value>org.apache.sentry.binding.hive.HiveAuthzBindingSessionHook'
    '</value>'
    '\n</property>'
    '\n<property>'
    '\n   <name>hive.sentry.conf.url</name>'
    '\n   <value>file:///{{CMF_CONF_DIR}}/sentry-site.xml</value>'
    '\n</property>')

HIVE_METASTORE_SENTRY_SAFETY_VALVE = (
    '<property>'
    '\n    <name>hive.metastore.client.impl</name>'
    '\n    <value>org.apache.sentry.binding.metastore.SentryHiveMetaStore'
    'Client</value>'
    '\n    <description>Sets custom Hive metastore client which Sentry uses'
    ' to filter out metadata.</description>'
    '\n</property>'
    '\n<property>'
    '\n    <name>hive.metastore.pre.event.listeners</name>'
    '\n    <value>org.apache.sentry.binding.metastore.MetastoreAuthzBinding'
    '</value>'
    '\n    <description>list of comma separated listeners for metastore'
    ' events.</description>'
    '\n</property>'
    '\n<property>'
    '\n    <name>hive.metastore.event.listeners</name>'
    '\n    <value>org.apache.sentry.binding.metastore.SentryMetastorePost'
    'EventListener</value>'
    '\n    <description>list of comma separated listeners for metastore,'
    ' post events.</description>'
    '\n</property>')

SENTRY_IMPALA_CLIENT_SAFETY_VALVE = (
    '<property>'
    '\n   <name>sentry.service.client.server.rpc-port</name>'
    '\n   <value>3893</value>'
    '\n</property>'
    '\n<property>'
    '\n   <name>sentry.service.client.server.rpc-address</name>'
    '\n   <value>hostname</value>'
    '\n</property>'
    '\n<property>'
    '\n   <name>sentry.service.client.server.rpc-connection-timeout</name>'
    '\n   <value>200000</value>'
    '\n</property>'
    '\n<property>'
    '\n   <name>sentry.service.security.mode</name>'
    '\n   <value>none</value>'
    '\n</property>')

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

ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                        config_type='bool', priority=1,
                        default_value=True)

ENABLE_HBASE_COMMON_LIB = p.Config('Enable HBase Common Lib',
                                   'general', 'cluster', config_type='bool',
                                   priority=1, default_value=True)

SWIFT_LIB_URL = p.Config(
    'Hadoop OpenStack library URL', 'general', 'cluster', priority=1,
    default_value=DEFAULT_SWIFT_LIB_URL,
    description=("Library that adds Swift support to CDH. The file will be "
                 "downloaded from VM."))


EXTJS_LIB_URL = p.Config(
    "ExtJS library URL", 'general', 'cluster', priority=1,
    default_value=DEFAULT_EXTJS_LIB_URL,
    description=("Ext 2.2 library is required for Oozie Web Console. "
                 "The file will be downloaded from VM with oozie."))


def _get_cluster_plugin_configs():
    return [CDH5_REPO_URL, CDH5_REPO_KEY_URL, CM5_REPO_URL, CM5_REPO_KEY_URL,
            ENABLE_SWIFT, ENABLE_HBASE_COMMON_LIB, SWIFT_LIB_URL,
            EXTJS_LIB_URL]


# ng wide configs

def _load_json(path_to_file):
    data = f.get_file_text(path_to_file)
    return json.loads(data)


path_to_config = 'plugins/cdh/v5_3_0/resources/'
hdfs_confs = _load_json(path_to_config + 'hdfs-service.json')
namenode_confs = _load_json(path_to_config + 'hdfs-namenode.json')
datanode_confs = _load_json(path_to_config + 'hdfs-datanode.json')
secnamenode_confs = _load_json(path_to_config + 'hdfs-secondarynamenode.json')
yarn_confs = _load_json(path_to_config + 'yarn-service.json')
resourcemanager_confs = _load_json(
    path_to_config + 'yarn-resourcemanager.json')
nodemanager_confs = _load_json(path_to_config + 'yarn-nodemanager.json')
jobhistory_confs = _load_json(path_to_config + 'yarn-jobhistory.json')
oozie_service_confs = _load_json(path_to_config + 'oozie-service.json')
oozie_role_confs = _load_json(path_to_config + 'oozie-oozie_server.json')
hive_service_confs = _load_json(path_to_config + 'hive-service.json')
hive_metastore_confs = _load_json(path_to_config + 'hive-hivemetastore.json')
hive_hiveserver_confs = _load_json(path_to_config + 'hive-hiveserver2.json')
hive_webhcat_confs = _load_json(path_to_config + 'hive-webhcat.json')
hue_service_confs = _load_json(path_to_config + 'hue-service.json')
hue_role_confs = _load_json(path_to_config + 'hue-hue_server.json')
spark_service_confs = _load_json(path_to_config + 'spark-service.json')
spark_role_confs = _load_json(
    path_to_config + 'spark-spark_yarn_history_server.json')
zookeeper_service_confs = _load_json(path_to_config + 'zookeeper-service.json')
zookeeper_server_confs = _load_json(path_to_config + 'zookeeper-server.json')
hbase_confs = _load_json(path_to_config + 'hbase-service.json')
master_confs = _load_json(path_to_config + 'hbase-master.json')
regionserver_confs = _load_json(path_to_config + 'hbase-regionserver.json')
flume_service_confs = _load_json(path_to_config + 'flume-service.json')
flume_agent_confs = _load_json(path_to_config + 'flume-agent.json')
sentry_service_confs = _load_json(path_to_config + 'sentry-service.json')
sentry_server_confs = _load_json(path_to_config +
                                 'sentry-sentry_server.json')
solr_service_confs = _load_json(path_to_config + 'solr-service.json')
solr_server_confs = _load_json(path_to_config + 'solr-solr_server.json')
sqoop_service_confs = _load_json(path_to_config + 'sqoop-service.json')
sqoop_server_confs = _load_json(path_to_config +
                                'sqoop-sqoop_server.json')
ks_indexer_service_confs = _load_json(path_to_config +
                                      'ks_indexer-service.json')
ks_indexer_role_confs = _load_json(path_to_config +
                                   'ks_indexer-hbase_indexer.json')
impala_service_confs = _load_json(path_to_config + 'impala-service.json')
impala_catalogserver_confs = _load_json(path_to_config +
                                        'impala-catalogserver.json')
impala_impalad_confs = _load_json(path_to_config +
                                  'impala-impalad.json')
impala_llama_confs = _load_json(path_to_config +
                                'impala-llama.json')
impala_statestore_confs = _load_json(path_to_config +
                                     'impala-statestore.json')

priority_one_confs = _load_json(path_to_config + 'priority-one-confs.json')


def _prepare_value(value):
    if not value:
        return ""

    return value.replace('\n', ' ')


def _init_configs(confs, app_target, scope):
    cfgs = []
    for cfg in confs:
        priority = 1 if cfg['name'] in priority_one_confs else 2
        c = p.Config(cfg['name'], app_target, scope, priority=priority,
                     default_value=_prepare_value(cfg['value']),
                     description=cfg['desc'], is_optional=True)
        cfgs.append(c)

    return cfgs


def _get_ng_plugin_configs():
    cfg = []
    cfg += _init_configs(hdfs_confs, 'HDFS', 'cluster')
    cfg += _init_configs(namenode_confs, 'NAMENODE', 'node')
    cfg += _init_configs(datanode_confs, 'DATANODE', 'node')
    cfg += _init_configs(secnamenode_confs, 'SECONDARYNAMENODE', 'node')
    cfg += _init_configs(yarn_confs, 'YARN', 'cluster')
    cfg += _init_configs(resourcemanager_confs, 'RESOURCEMANAGER', 'node')
    cfg += _init_configs(nodemanager_confs, 'NODEMANAGER', 'node')
    cfg += _init_configs(jobhistory_confs, 'JOBHISTORY', 'node')
    cfg += _init_configs(oozie_service_confs, 'OOZIE', 'cluster')
    cfg += _init_configs(oozie_role_confs, 'OOZIE', 'node')
    cfg += _init_configs(hive_service_confs, 'HIVE', 'cluster')
    cfg += _init_configs(hive_metastore_confs, 'HIVEMETASTORE', 'node')
    cfg += _init_configs(hive_hiveserver_confs, 'HIVESERVER', 'node')
    cfg += _init_configs(hive_webhcat_confs, 'WEBHCAT', 'node')
    cfg += _init_configs(hue_service_confs, 'HUE', 'cluster')
    cfg += _init_configs(hue_role_confs, 'HUE', 'node')
    cfg += _init_configs(spark_service_confs, 'SPARK_ON_YARN', 'cluster')
    cfg += _init_configs(spark_role_confs, 'SPARK_ON_YARN', 'node')
    cfg += _init_configs(zookeeper_service_confs, 'ZOOKEEPER', 'cluster')
    cfg += _init_configs(zookeeper_server_confs, 'ZOOKEEPER', 'node')
    cfg += _init_configs(hbase_confs, 'HBASE', 'cluster')
    cfg += _init_configs(master_confs, 'MASTER', 'node')
    cfg += _init_configs(regionserver_confs, 'REGIONSERVER', 'node')
    cfg += _init_configs(flume_service_confs, 'FLUME', 'cluster')
    cfg += _init_configs(flume_agent_confs, 'FLUME', 'node')
    cfg += _init_configs(sentry_service_confs, 'SENTRY', 'cluster')
    cfg += _init_configs(sentry_server_confs, 'SENTRY', 'node')
    cfg += _init_configs(solr_service_confs, 'SOLR', 'cluster')
    cfg += _init_configs(solr_server_confs, 'SOLR', 'node')
    cfg += _init_configs(sqoop_service_confs, 'SQOOP', 'cluster')
    cfg += _init_configs(sqoop_server_confs, 'SQOOP', 'node')
    cfg += _init_configs(ks_indexer_service_confs, 'KS_INDEXER', 'cluster')
    cfg += _init_configs(ks_indexer_role_confs, 'KS_INDEXER', 'node')
    cfg += _init_configs(impala_service_confs, 'IMPALA', 'cluster')
    cfg += _init_configs(impala_catalogserver_confs, 'CATALOGSERVER', 'node')
    cfg += _init_configs(impala_impalad_confs, 'IMPALAD', 'node')
    cfg += _init_configs(impala_statestore_confs, 'STATESTORE', 'node')
    return cfg


def get_plugin_configs():
    cluster_wide = _get_cluster_plugin_configs()
    ng_wide = _get_ng_plugin_configs()
    return cluster_wide + ng_wide


def _get_config_value(cluster, key):
    return cluster.cluster_configs.get(
        'general', {}).get(key.name, key.default_value)


def get_cdh5_repo_url(cluster):
    return _get_config_value(cluster, CDH5_REPO_URL)


def get_cdh5_key_url(cluster):
    return _get_config_value(cluster, CDH5_REPO_KEY_URL)


def get_cm5_repo_url(cluster):
    return _get_config_value(cluster, CM5_REPO_URL)


def get_cm5_key_url(cluster):
    return _get_config_value(cluster, CM5_REPO_KEY_URL)


def is_swift_enabled(cluster):
    return _get_config_value(cluster, ENABLE_SWIFT)


def is_hbase_common_lib_enabled(cluster):
    return _get_config_value(cluster, ENABLE_HBASE_COMMON_LIB)


def get_swift_lib_url(cluster):
    return _get_config_value(cluster, SWIFT_LIB_URL)


def get_extjs_lib_url(cluster):
    return _get_config_value(cluster, EXTJS_LIB_URL)
