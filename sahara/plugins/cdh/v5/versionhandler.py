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

from sahara.plugins.cdh import abstractversionhandler as avm
from sahara.plugins.cdh.v5 import cloudera_utils
from sahara.plugins.cdh.v5 import config_helper
from sahara.plugins.cdh.v5 import deploy
from sahara.plugins.cdh.v5 import edp_engine
from sahara.plugins.cdh.v5 import plugin_utils
from sahara.plugins.cdh.v5 import validation


class VersionHandler(avm.BaseVersionHandler):

    def __init__(self):
        super(VersionHandler, self).__init__()
        self.config_helper = config_helper.ConfigHelperV5()
        self.cloudera_utils = cloudera_utils.ClouderaUtilsV5()
        self.plugin_utils = plugin_utils.PluginUtilsV5()
        self.deploy = deploy
        self.edp_engine = edp_engine
        self.validation = validation.ValidatorV5()

    def get_node_processes(self):
        return {
            "CLOUDERA": ['CLOUDERA_MANAGER'],
            "HDFS": ['HDFS_NAMENODE', 'HDFS_DATANODE',
                     'HDFS_SECONDARYNAMENODE'],
            "YARN": ['YARN_RESOURCEMANAGER', 'YARN_NODEMANAGER',
                     'YARN_JOBHISTORY'],
            "OOZIE": ['OOZIE_SERVER'],
            "HIVE": ['HIVE_SERVER2', 'HIVE_METASTORE', 'HIVE_WEBHCAT'],
            "HUE": ['HUE_SERVER'],
            "SPARK_ON_YARN": ['SPARK_YARN_HISTORY_SERVER'],
            "ZOOKEEPER": ['ZOOKEEPER_SERVER'],
            "HBASE": ['HBASE_MASTER', 'HBASE_REGIONSERVER'],
            "YARN_GATEWAY": [],
            "HDFS_GATEWAY": []
        }
