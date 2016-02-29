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


class ConfigHelperV5(c_h.ConfigHelper):
    path_to_config = 'plugins/cdh/v5/resources/'

    CDH5_UBUNTU_REPO = (
        'deb [arch=amd64] http://archive.cloudera.com/cdh5'
        '/ubuntu/precise/amd64/cdh precise-cdh5.0.0 contrib'
        '\ndeb-src http://archive.cloudera.com/cdh5/ubuntu'
        '/precise/amd64/cdh precise-cdh5.0.0 contrib')

    DEFAULT_CDH5_UBUNTU_REPO_KEY_URL = (
        'http://archive.cloudera.com/cdh5/ubuntu'
        '/precise/amd64/cdh/archive.key')

    CM5_UBUNTU_REPO = (
        'deb [arch=amd64] http://archive.cloudera.com/cm5'
        '/ubuntu/precise/amd64/cm precise-cm5.0.0 contrib'
        '\ndeb-src http://archive.cloudera.com/cm5/ubuntu'
        '/precise/amd64/cm precise-cm5.0.0 contrib')

    DEFAULT_CM5_UBUNTU_REPO_KEY_URL = (
        'http://archive.cloudera.com/cm5/ubuntu'
        '/precise/amd64/cm/archive.key')

    CDH5_CENTOS_REPO = (
        '[cloudera-cdh5]'
        '\nname=Cloudera\'s Distribution for Hadoop, Version 5'
        '\nbaseurl=http://archive.cloudera.com/cdh5/redhat/6'
        '/x86_64/cdh/5.0.0/'
        '\ngpgkey = http://archive.cloudera.com/cdh5/redhat/6'
        '/x86_64/cdh/RPM-GPG-KEY-cloudera'
        '\ngpgcheck = 1')

    CM5_CENTOS_REPO = (
        '[cloudera-manager]'
        '\nname=Cloudera Manager'
        '\nbaseurl=http://archive.cloudera.com/cm5/redhat/6'
        '/x86_64/cm/5.0.0/'
        '\ngpgkey = http://archive.cloudera.com/cm5/redhat/6'
        '/x86_64/cm/RPM-GPG-KEY-cloudera'
        '\ngpgcheck = 1')

    def __init__(self):
        super(ConfigHelperV5, self).__init__()
        self.priority_one_confs = self._load_json(
            self.path_to_config + 'priority-one-confs.json')
        self._load_ng_plugin_configs()

    def _load_ng_plugin_configs(self):
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
        self.yarn_confs = self._load_and_init_configs(
            'yarn-service.json', 'YARN', 'cluster')
        self.resourcemanager_confs = self._load_and_init_configs(
            'yarn-resourcemanager.json', 'YARN_GATEWAY', 'node')
        self.nodemanager_confs = self._load_and_init_configs(
            'yarn-nodemanager.json', 'RESOURCEMANAGER', 'node')
        self.jobhistory_confs = self._load_and_init_configs(
            'yarn-jobhistory.json', 'NODEMANAGER', 'node')
        self.yarn_gateway = self._load_and_init_configs(
            'yarn-gateway.json', 'JOBHISTORY', 'node')
        self.oozie_service_confs = self._load_and_init_configs(
            'oozie-service.json', 'OOZIE', 'cluster')
        self.oozie_role_confs = self._load_and_init_configs(
            'oozie-oozie.json', 'OOZIE', 'node')
        self.hive_service_confs = self._load_and_init_configs(
            'hive-service.json', 'HIVE', 'cluster')
        self.hive_metastore_confs = self._load_and_init_configs(
            'hive-metastore.json', 'HIVEMETASTORE', 'node')
        self.hive_hiveserver_confs = self._load_and_init_configs(
            'hive-hiveserver2.json', 'HIVESERVER', 'node')
        self.hive_webhcat_confs = self._load_and_init_configs(
            'hive-webhcat.json', 'WEBHCAT', 'node')
        self.hue_service_confs = self._load_and_init_configs(
            'hue-service.json', 'HUE', 'cluster')
        self.hue_role_confs = self._load_and_init_configs(
            'hue-hue.json', 'HUE', 'node')
        self.spark_service_confs = self._load_and_init_configs(
            'spark-service.json', 'SPARK_ON_YARN', 'cluster')
        self.spark_role_confs = self._load_and_init_configs(
            'spark-history.json', 'SPARK_ON_YARN', 'node')
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
