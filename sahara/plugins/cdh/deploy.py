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

from sahara.plugins import kerberos


PACKAGES = [
    'cloudera-manager-agent',
    'cloudera-manager-daemons',
    'cloudera-manager-server',
    'cloudera-manager-server-db-2',
    'flume-ng',
    'hadoop-hdfs-datanode',
    'hadoop-hdfs-namenode',
    'hadoop-hdfs-secondarynamenode',
    'hadoop-kms'
    'hadoop-mapreduce',
    'hadoop-mapreduce-historyserver',
    'hadoop-yarn-nodemanager',
    'hadoop-yarn-resourcemanager',
    'hbase',
    'hbase-solr',
    'hive-hcatalog',
    'hive-metastore',
    'hive-server2',
    'hive-webhcat-server',
    'hue',
    'impala',
    'impala-server',
    'impala-state-store',
    'impala-catalog',
    'impala-shell',
    'kafka',
    'kafka-server'
    'keytrustee-keyprovider',
    'oozie',
    'oracle-j2sdk1.7',
    'sentry',
    'solr-server',
    'solr-doc',
    'search',
    'spark-history-server',
    'sqoop2',
    'unzip',
    'zookeeper'
]


def setup_kerberos_for_cluster(cluster, cloudera_utils):
    if kerberos.is_kerberos_security_enabled(cluster):
        manager = cloudera_utils.pu.get_manager(cluster)
        kerberos.deploy_infrastructure(cluster, manager)
        cloudera_utils.full_cluster_stop(cluster)
        kerberos.prepare_policy_files(cluster)
        cloudera_utils.push_kerberos_configs(cluster)
        cloudera_utils.full_cluster_start(cluster)
        kerberos.create_keytabs_for_map(
            cluster,
            {'hdfs': cloudera_utils.pu.get_hdfs_nodes(cluster),
             'spark': [cloudera_utils.pu.get_spark_historyserver(cluster)]})


def prepare_scaling_kerberized_cluster(cluster, cloudera_utils, instances):
    if kerberos.is_kerberos_security_enabled(cluster):
        server = None
        if not kerberos.using_existing_kdc(cluster):
            server = cloudera_utils.pu.get_manager(cluster)
        kerberos.setup_clients(cluster, server)
        kerberos.prepare_policy_files(cluster)
        # manager can correctly handle updating configs
        cloudera_utils.push_kerberos_configs(cluster)
        kerberos.create_keytabs_for_map(
            cluster,
            {'hdfs': cloudera_utils.pu.get_hdfs_nodes(cluster, instances)})


def get_open_ports(node_group):
    ports = [9000]  # for CM agent

    ports_map = {
        'CLOUDERA_MANAGER': [7180, 7182, 7183, 7432, 7184, 8084, 8086, 10101,
                             9997, 9996, 8087, 9998, 9999, 8085, 9995, 9994],
        'HDFS_NAMENODE': [8020, 8022, 50070, 50470],
        'HDFS_SECONDARYNAMENODE': [50090, 50495],
        'HDFS_DATANODE': [50010, 1004, 50075, 1006, 50020],
        'YARN_RESOURCEMANAGER': [8030, 8031, 8032, 8033, 8088],
        'YARN_STANDBYRM': [8030, 8031, 8032, 8033, 8088],
        'YARN_NODEMANAGER': [8040, 8041, 8042],
        'YARN_JOBHISTORY': [10020, 19888],
        'HIVE_METASTORE': [9083],
        'HIVE_SERVER2': [10000],
        'HUE_SERVER': [8888],
        'OOZIE_SERVER': [11000, 11001],
        'SPARK_YARN_HISTORY_SERVER': [18088],
        'ZOOKEEPER_SERVER': [2181, 3181, 4181, 9010],
        'HBASE_MASTER': [60000],
        'HBASE_REGIONSERVER': [60020],
        'FLUME_AGENT': [41414],
        'SENTRY_SERVER': [8038],
        'SOLR_SERVER': [8983, 8984],
        'SQOOP_SERVER': [8005, 12000],
        'KEY_VALUE_STORE_INDEXER': [],
        'IMPALA_CATALOGSERVER': [25020, 26000],
        'IMPALA_STATESTORE': [25010, 24000],
        'IMPALAD': [21050, 21000, 23000, 25000, 28000, 22000],
        'KMS': [16000, 16001],
        'JOURNALNODE': [8480, 8481, 8485]
    }

    for process in node_group.node_processes:
        if process in ports_map:
            ports.extend(ports_map[process])

    return ports
