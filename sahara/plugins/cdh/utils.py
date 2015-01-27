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

from sahara.conductor import resource as res
from sahara.plugins import utils as u


def get_manager(cluster):
    return u.get_instance(cluster, 'CLOUDERA_MANAGER')


def get_namenode(cluster):
    return u.get_instance(cluster, 'HDFS_NAMENODE')


def get_secondarynamenode(cluster):
    return u.get_instance(cluster, 'HDFS_SECONDARYNAMENODE')


def get_datanodes(cluster):
    return u.get_instances(cluster, 'HDFS_DATANODE')


def get_resourcemanager(cluster):
    return u.get_instance(cluster, 'YARN_RESOURCEMANAGER')


def get_nodemanagers(cluster):
    return u.get_instances(cluster, 'YARN_NODEMANAGER')


def get_historyserver(cluster):
    return u.get_instance(cluster, 'YARN_JOBHISTORY')


def get_oozie(cluster):
    return u.get_instance(cluster, 'OOZIE_SERVER')


def get_hive_metastore(cluster):
    return u.get_instance(cluster, 'HIVE_METASTORE')


def get_hive_servers(cluster):
    return u.get_instances(cluster, 'HIVE_SERVER2')


def get_hue(cluster):
    return u.get_instance(cluster, 'HUE_SERVER')


def get_spark_historyserver(cluster):
    return u.get_instance(cluster, 'SPARK_YARN_HISTORY_SERVER')


def get_zookeepers(cluster):
    return u.get_instances(cluster, 'ZOOKEEPER_SERVER')


def get_hbase_master(cluster):
    return u.get_instance(cluster, 'HBASE_MASTER')


def get_flumes(cluster):
    return u.get_instances(cluster, 'FLUME_AGENT')


def get_sentry(cluster):
    return u.get_instance(cluster, 'SENTRY_SERVER')


def get_solrs(cluster):
    return u.get_instances(cluster, 'SOLR_SERVER')


def get_sqoop(cluster):
    return u.get_instance(cluster, 'SQOOP_SERVER')


def get_hbase_indexers(cluster):
    return u.get_instances(cluster, 'KEY_VALUE_STORE_INDEXER')


def get_catalogserver(cluster):
    return u.get_instance(cluster, 'IMPALA_CATALOGSERVER')


def get_statestore(cluster):
    return u.get_instance(cluster, 'IMPALA_STATESTORE')


def get_impalads(cluster):
    return u.get_instances(cluster, 'IMPALAD')


def convert_process_configs(configs):
    p_dict = {
        "CLOUDERA": ['MANAGER'],
        "NAMENODE": ['NAMENODE'],
        "DATANODE": ['DATANODE'],
        "SECONDARYNAMENODE": ['SECONDARYNAMENODE'],
        "RESOURCEMANAGER": ['RESOURCEMANAGER'],
        "NODEMANAGER": ['NODEMANAGER'],
        "JOBHISTORY": ['JOBHISTORY'],
        "OOZIE": ['OOZIE_SERVER'],
        "HIVESERVER": ['HIVESERVER2'],
        "HIVEMETASTORE": ['HIVEMETASTORE'],
        "WEBHCAT": ['WEBHCAT'],
        "HUE": ['HUE_SERVER'],
        "SPARK_ON_YARN": ['SPARK_YARN_HISTORY_SERVER'],
        "ZOOKEEPER": ['SERVER'],
        "MASTER": ['MASTER'],
        "REGIONSERVER": ['REGIONSERVER'],
        "FLUME": ['AGENT'],
        "CATALOGSERVER": ['CATALOGSERVER'],
        "STATESTORE": ['STATESTORE'],
        "IMPALAD": ['IMPALAD'],
        "KS_INDEXER": ['HBASE_INDEXER'],
        "SENTRY": ['SENTRY_SERVER'],
        "SOLR": ['SOLR_SERVER'],
        "SQOOP": ['SQOOP_SERVER']
    }
    if isinstance(configs, res.Resource):
        configs = configs.to_dict()
    for k in configs.keys():
        if k in p_dict.keys():
            item = configs[k]
            del configs[k]
            newkey = p_dict[k][0]
            configs[newkey] = item
    return res.Resource(configs)


def convert_role_showname(showname):
    name_dict = {
        'CLOUDERA_MANAGER': 'MANAGER',
        'HDFS_NAMENODE': 'NAMENODE',
        'HDFS_DATANODE': 'DATANODE',
        'HDFS_SECONDARYNAMENODE': 'SECONDARYNAMENODE',
        'YARN_RESOURCEMANAGER': 'RESOURCEMANAGER',
        'YARN_NODEMANAGER': 'NODEMANAGER',
        'YARN_JOBHISTORY': 'JOBHISTORY',
        'OOZIE_SERVER': 'OOZIE_SERVER',
        'HIVE_SERVER2': 'HIVESERVER2',
        'HIVE_METASTORE': 'HIVEMETASTORE',
        'HIVE_WEBHCAT': 'WEBHCAT',
        'HUE_SERVER': 'HUE_SERVER',
        'SPARK_YARN_HISTORY_SERVER': 'SPARK_YARN_HISTORY_SERVER',
        'ZOOKEEPER_SERVER': 'SERVER',
        'HBASE_MASTER': 'MASTER',
        'HBASE_REGIONSERVER': 'REGIONSERVER',
        'FLUME_AGENT': 'AGENT',
        'IMPALA_CATALOGSERVER': 'CATALOGSERVER',
        'IMPALA_STATESTORE': 'STATESTORE',
        'IMPALAD': 'IMPALAD',
        'KEY_VALUE_STORE_INDEXER': 'HBASE_INDEXER',
        'SENTRY_SERVER': 'SENTRY_SERVER',
        'SOLR_SERVER': 'SOLR_SERVER',
        'SQOOP_SERVER': 'SQOOP_SERVER',
    }
    return name_dict.get(showname, None)
