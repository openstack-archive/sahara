# Copyright (c) 2015 Intel Corporation
# Copyright (c) 2015 ISPRAS
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

from sahara.plugins.cdh import abstractversionhandler as avm
from sahara.plugins.cdh.v5_4_0 import cloudera_utils
from sahara.plugins.cdh.v5_4_0 import config_helper
from sahara.plugins.cdh.v5_4_0 import deploy
from sahara.plugins.cdh.v5_4_0 import edp_engine
from sahara.plugins.cdh.v5_4_0 import plugin_utils
from sahara.plugins.cdh.v5_4_0 import validation


class VersionHandler(avm.BaseVersionHandler):

    def __init__(self):
        super(VersionHandler, self).__init__()
        self.config_helper = config_helper.ConfigHelperV540()
        self.cloudera_utils = cloudera_utils.ClouderaUtilsV540()
        self.plugin_utils = plugin_utils.PluginUtilsV540()
        self.deploy = deploy
        self.edp_engine = edp_engine
        self.validation = validation.ValidatorV540()

    def get_node_processes(self):
        return {
            "CLOUDERA": ['CLOUDERA_MANAGER'],
            "HDFS": ['HDFS_NAMENODE', 'HDFS_DATANODE',
                     'HDFS_SECONDARYNAMENODE', 'HDFS_JOURNALNODE'],
            "YARN": ['YARN_RESOURCEMANAGER', 'YARN_NODEMANAGER',
                     'YARN_JOBHISTORY', 'YARN_STANDBYRM'],
            "OOZIE": ['OOZIE_SERVER'],
            "HIVE": ['HIVE_SERVER2', 'HIVE_METASTORE', 'HIVE_WEBHCAT'],
            "HUE": ['HUE_SERVER'],
            "SPARK_ON_YARN": ['SPARK_YARN_HISTORY_SERVER'],
            "ZOOKEEPER": ['ZOOKEEPER_SERVER'],
            "HBASE": ['HBASE_MASTER', 'HBASE_REGIONSERVER'],
            "FLUME": ['FLUME_AGENT'],
            "IMPALA": ['IMPALA_CATALOGSERVER', 'IMPALA_STATESTORE', 'IMPALAD'],
            "KS_INDEXER": ['KEY_VALUE_STORE_INDEXER'],
            "SOLR": ['SOLR_SERVER'],
            "SQOOP": ['SQOOP_SERVER'],
            "SENTRY": ['SENTRY_SERVER'],
            "KMS": ['KMS'],

            "YARN_GATEWAY": [],
            "RESOURCEMANAGER": [],
            "NODEMANAGER": [],
            "JOBHISTORY": [],

            "HDFS_GATEWAY": [],
            'DATANODE': [],
            'NAMENODE': [],
            'SECONDARYNAMENODE': [],
            'JOURNALNODE': [],

            'REGIONSERVER': [],
            'MASTER': [],

            'HIVEMETASTORE': [],
            'HIVESERVER': [],
            'WEBCAT': [],

            'CATALOGSERVER': [],
            'STATESTORE': [],
            'IMPALAD': [],
        }

    def get_edp_engine(self, cluster, job_type):
        oozie_type = self.edp_engine.EdpOozieEngine.get_supported_job_types()
        spark_type = self.edp_engine.EdpSparkEngine.get_supported_job_types()
        if job_type in oozie_type:
            return self.edp_engine.EdpOozieEngine(cluster)
        if job_type in spark_type:
            return self.edp_engine.EdpSparkEngine(cluster)
        return None

    def get_edp_job_types(self):
        return (edp_engine.EdpOozieEngine.get_supported_job_types() +
                edp_engine.EdpSparkEngine.get_supported_job_types())
