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


# define service names

AMBARI_SERVICE = "Ambari"
HDFS_SERVICE = "HDFS"
RANGER_SERVICE = "Ranger"
YARN_SERVICE = "YARN"
ZOOKEEPER_SERVICE = "ZooKeeper"
HIVE_SERVICE = "Hive"
OOZIE_SERVICE = "Oozie"

# define process names

AMBARI_SERVER = "Ambari"
APP_TIMELINE_SERVER = "YARN Timeline Server"
DATANODE = "DataNode"
HISTORYSERVER = "MapReduce History Server"
HIVE_METASTORE = "Hive Metastore"
HIVE_SERVER = "HiveServer"
NAMENODE = "NameNode"
NODEMANAGER = "NodeManager"
OOZIE_SERVER = "Oozie"
RESOURCEMANAGER = "ResourceManager"
SECONDARY_NAMENODE = "SecondaryNameNode"
ZOOKEEPER_SERVER = "ZooKeeper"


PROC_MAP = {
    AMBARI_SERVER: ["METRICS_COLLECTOR"],
    APP_TIMELINE_SERVER: ["APP_TIMELINE_SERVER"],
    DATANODE: ["DATANODE"],
    HISTORYSERVER: ["HISTORYSERVER"],
    HIVE_METASTORE: ["HIVE_METASTORE"],
    HIVE_SERVER: ["HIVE_SERVER", "MYSQL_SERVER", "WEBHCAT_SERVER"],
    NAMENODE: ["NAMENODE"],
    NODEMANAGER: ["NODEMANAGER"],
    OOZIE_SERVER: ["OOZIE_SERVER", "PIG"],
    RESOURCEMANAGER: ["RESOURCEMANAGER"],
    SECONDARY_NAMENODE: ["SECONDARY_NAMENODE"],
    ZOOKEEPER_SERVER: ["ZOOKEEPER_SERVER"]
}

CLIENT_MAP = {
    APP_TIMELINE_SERVER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    DATANODE: ["HDFS_CLIENT"],
    HISTORYSERVER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    HIVE_METASTORE: ["HIVE_CLIENT"],
    HIVE_SERVER: ["HIVE_CLIENT"],
    NAMENODE: ["HDFS_CLIENT"],
    NODEMANAGER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    OOZIE_SERVER: ["OOZIE_CLIENT", "TEZ_CLIENT"],
    RESOURCEMANAGER: ["MAPREDUCE2_CLIENT", "YARN_CLIENT"],
    SECONDARY_NAMENODE: ["HDFS_CLIENT"],
    ZOOKEEPER_SERVER: ["ZOOKEEPER_CLIENT"]
}

ALL_LIST = ["METRICS_MONITOR"]


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
    return clients
