# Copyright (c) 2014 Intel Corporation.
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

from sahara.plugins.cdh import plugin_utils as pu
from sahara.plugins.cdh.v5 import config_helper
from sahara.plugins.cdh.v5 import db_helper


class PluginUtilsV5(pu.AbstractPluginUtils):

    def __init__(self):
        self.c_helper = config_helper.ConfigHelperV5()
        self.db_helper = db_helper

    def configure_spark(self, cluster):
        spark = self.get_spark_historyserver(cluster)
        with spark.remote() as r:
            r.execute_command(
                'sudo su - -c "hdfs dfs -mkdir -p '
                '/user/spark/applicationHistory" hdfs')
            r.execute_command(
                'sudo su - -c "hdfs dfs -mkdir -p '
                '/user/spark/share/lib" hdfs')
            r.execute_command(
                'sudo su - -c "hdfs dfs -put /usr/lib/spark/assembly/lib/'
                'spark-assembly-hadoop* '
                '/user/spark/share/lib/spark-assembly.jar" hdfs')
            r.execute_command(
                'sudo su - -c "hdfs dfs -chown -R '
                'spark:spark /user/spark" hdfs')
            r.execute_command(
                'sudo su - -c "hdfs dfs -chmod 0751 /user/spark" hdfs')
            r.execute_command(
                'sudo su - -c "hdfs dfs -chmod 1777 /user/spark/'
                'applicationHistory" hdfs')

    def create_hive_hive_directory(self, cluster):
        # Hive requires /tmp/hive-hive directory
        namenode = self.get_namenode(cluster)
        with namenode.remote() as r:
            r.execute_command(
                'sudo su - -c "hadoop fs -mkdir -p /tmp/hive-hive" hdfs')
            r.execute_command(
                'sudo su - -c "hadoop fs -chown hive /tmp/hive-hive" hdfs')
