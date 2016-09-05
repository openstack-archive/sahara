# Copyright (c) 2015 Mirantis Inc.
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

from sahara.plugins import kerberos

# define service names

AMBARI_SERVICE = "Ambari"
FALCON_SERVICE = "Falcon"
FLUME_SERVICE = "Flume"
HBASE_SERVICE = "HBase"
HDFS_SERVICE = "HDFS"
HIVE_SERVICE = "Hive"
KAFKA_SERVICE = "Kafka"
KNOX_SERVICE = "Knox"
MAPREDUCE2_SERVICE = "MAPREDUCE2"
OOZIE_SERVICE = "Oozie"
RANGER_SERVICE = "Ranger"
SLIDER_SERVICE = "Slider"
SPARK_SERVICE = "Spark"
SQOOP_SERVICE = "Sqoop"
STORM_SERVICE = "Storm"
YARN_SERVICE = "YARN"
ZOOKEEPER_SERVICE = "ZooKeeper"

# define process names

AMBARI_SERVER = "Ambari"
APP_TIMELINE_SERVER = "YARN Timeline Server"
DATANODE = "DataNode"
DRPC_SERVER = "DRPC Server"
FALCON_SERVER = "Falcon Server"
FLUME_HANDLER = "Flume"
HBASE_MASTER = "HBase Master"
HBASE_REGIONSERVER = "HBase RegionServer"
HISTORYSERVER = "MapReduce History Server"
HIVE_METASTORE = "Hive Metastore"
HIVE_SERVER = "HiveServer"
KAFKA_BROKER = "Kafka Broker"
KNOX_GATEWAY = "Knox Gateway"
NAMENODE = "NameNode"
NIMBUS = "Nimbus"
NODEMANAGER = "NodeManager"
OOZIE_SERVER = "Oozie"
RANGER_ADMIN = "Ranger Admin"
RANGER_USERSYNC = "Ranger Usersync"
RESOURCEMANAGER = "ResourceManager"
SECONDARY_NAMENODE = "SecondaryNameNode"
SLIDER = "Slider"
SPARK_JOBHISTORYSERVER = "Spark History Server"
SQOOP = "Sqoop"
STORM_UI_SERVER = "Storm UI Server"
SUPERVISOR = "Supervisor"
ZOOKEEPER_SERVER = "ZooKeeper"
JOURNAL_NODE = "JournalNode"


PROC_MAP = {
    AMBARI_SERVER: ["METRICS_COLLECTOR"],
    APP_TIMELINE_SERVER: ["APP_TIMELINE_SERVER"],
    DATANODE: ["DATANODE"],
    DRPC_SERVER: ["DRPC_SERVER"],
    FALCON_SERVER: ["FALCON_SERVER"],
    HBASE_MASTER: ["HBASE_MASTER"],
    HBASE_REGIONSERVER: ["HBASE_REGIONSERVER"],
    HISTORYSERVER: ["HISTORYSERVER"],
    HIVE_METASTORE: ["HIVE_METASTORE"],
    HIVE_SERVER: ["HIVE_SERVER", "MYSQL_SERVER", "WEBHCAT_SERVER"],
    KAFKA_BROKER: ["KAFKA_BROKER"],
    KNOX_GATEWAY: ["KNOX_GATEWAY"],
    NAMENODE: ["NAMENODE"],
    NIMBUS: ["NIMBUS"],
    NODEMANAGER: ["NODEMANAGER"],
    OOZIE_SERVER: ["OOZIE_SERVER", "PIG"],
    RANGER_ADMIN: ["RANGER_ADMIN"],
    RANGER_USERSYNC: ["RANGER_USERSYNC"],
    RESOURCEMANAGER: ["RESOURCEMANAGER"],
    SECONDARY_NAMENODE: ["SECONDARY_NAMENODE"],
    SLIDER: ["SLIDER"],
    SPARK_JOBHISTORYSERVER: ["SPARK_JOBHISTORYSERVER"],
    SQOOP: ["SQOOP"],
    STORM_UI_SERVER: ["STORM_UI_SERVER"],
    SUPERVISOR: ["SUPERVISOR"],
    ZOOKEEPER_SERVER: ["ZOOKEEPER_SERVER"],
    JOURNAL_NODE: ["JOURNALNODE"]
}

CLIENT_MAP = {
    APP_TIMELINE_SERVER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    DATANODE: ["HDFS_CLIENT"],
    FALCON_SERVER: ["FALCON_CLIENT"],
    FLUME_HANDLER: ["FLUME_HANDLER"],
    HBASE_MASTER: ["HBASE_CLIENT"],
    HBASE_REGIONSERVER: ["HBASE_CLIENT"],
    HISTORYSERVER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    HIVE_METASTORE: ["HIVE_CLIENT"],
    HIVE_SERVER: ["HIVE_CLIENT"],
    NAMENODE: ["HDFS_CLIENT"],
    NODEMANAGER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    OOZIE_SERVER: ["OOZIE_CLIENT", "TEZ_CLIENT"],
    RESOURCEMANAGER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    SECONDARY_NAMENODE: ["HDFS_CLIENT"],
    SPARK_JOBHISTORYSERVER: ["SPARK_CLIENT"],
    ZOOKEEPER_SERVER: ["ZOOKEEPER_CLIENT"]
}

KERBEROS_CLIENT = 'KERBEROS_CLIENT'
ALL_LIST = ["METRICS_MONITOR"]

# types of HA
NAMENODE_HA = "NameNode HA"
RESOURCEMANAGER_HA = "ResourceManager HA"
HBASE_REGIONSERVER_HA = "HBase RegionServer HA"


def get_ambari_proc_list(node_group):
    procs = []
    for sp in node_group.node_processes:
        procs.extend(PROC_MAP.get(sp, []))
    return procs


def get_clients(cluster):
    procs = []
    for ng in cluster.node_groups:
        procs.extend(ng.node_processes)

    clients = []
    for proc in procs:
        clients.extend(CLIENT_MAP.get(proc, []))
    clients = list(set(clients))
    clients.extend(ALL_LIST)
    if kerberos.is_kerberos_security_enabled(cluster):
        clients.append(KERBEROS_CLIENT)
    return clients


def instances_have_process(instances, process):
    for i in instances:
        if process in i.node_group.node_processes:
            return True

    return False
