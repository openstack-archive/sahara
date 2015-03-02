# Copyright (c) 2013 Mirantis Inc.
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

from __future__ import print_function

import os
import sys

from oslo_config import cfg


def singleton(cls):
    instances = {}

    def get_instance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]

    return get_instance


COMMON_CONFIG_GROUP = cfg.OptGroup(name='COMMON')
COMMON_CONFIG_OPTS = [
    cfg.StrOpt('OS_USERNAME',
               default='admin',
               help='Username for OpenStack.'),
    cfg.StrOpt('OS_PASSWORD',
               default='admin',
               help='Password for OpenStack.'),
    cfg.StrOpt('OS_TENANT_NAME',
               default='admin',
               help='Tenant name for OpenStack.'),
    cfg.StrOpt('OS_AUTH_URL',
               default='http://127.0.0.1:5000/v2.0',
               help='URL for OpenStack.'),
    cfg.StrOpt('SWIFT_AUTH_VERSION',
               default=2,
               help='OpenStack auth version for Swift.'),
    cfg.StrOpt('SAHARA_HOST',
               default='127.0.0.1',
               help='Host for Sahara.'),
    cfg.IntOpt('SAHARA_PORT',
               default=8386,
               help='Port for Sahara.'),
    cfg.StrOpt('SAHARA_API_VERSION',
               default='1.1',
               help='API version for Sahara.'),
    cfg.StrOpt('FLAVOR_ID',
               help='OpenStack flavor ID for virtual machines. If you leave '
                    'the default value of this parameter, then flavor ID will '
                    'be created automatically, using nova client. The created '
                    'flavor will have the following parameters: '
                    'name=i-test-flavor-<id>, ram=1024, vcpus=1, disk=10, '
                    'ephemeral=10. <id> is ID of 8 characters '
                    '(letters and/or digits) which is added to name of flavor '
                    'for its uniqueness.'),
    cfg.IntOpt('CLUSTER_CREATION_TIMEOUT',
               default=30,
               help='Cluster creation timeout (in minutes); '
                    'minimal value is 1.'),
    cfg.IntOpt('TELNET_TIMEOUT',
               default=5,
               help='Timeout for node process deployment on cluster '
                    'nodes (in minutes); minimal value is 1.'),
    cfg.IntOpt('HDFS_INITIALIZATION_TIMEOUT',
               default=5,
               help='Timeout for HDFS initialization (in minutes); '
                    'minimal value is 1.'),
    cfg.IntOpt('JOB_LAUNCH_TIMEOUT',
               default=5,
               help='Timeout for job launch (in minutes); '
                    'minimal value is 1.'),
    cfg.IntOpt('TRANSIENT_CLUSTER_TIMEOUT',
               default=3,
               help='Timeout for a poll of state of transient cluster '
                    '(in minutes); minimal value is 1.'),
    cfg.IntOpt('DELETE_RESOURCE_TIMEOUT',
               default=5,
               help='Timeout for a removing resource '
                    '(in minutes); minimal value is 1.'),
    cfg.StrOpt('CLUSTER_NAME',
               default='test-cluster',
               help='Name for cluster.'),
    cfg.StrOpt('USER_KEYPAIR_ID',
               default='sahara-i-test-key-pair',
               help='OpenStack key pair ID of your SSH public key. Sahara '
                    'transfers this key to cluster nodes for access by users '
                    'to virtual machines of cluster via SSH. You can export '
                    'your id_rsa.pub public key to OpenStack and specify its '
                    'key pair ID in configuration file of tests. If you '
                    'already have a key pair in OpenStack, then you just '
                    'should specify its key pair ID in configuration file of '
                    'tests. If you have no key pair in OpenStack or you do '
                    'not want to export (create) key pair then you just '
                    'should specify any key pair ID which you like (for '
                    'example, "king-kong") but you have necessarily to leave '
                    'default value of PATH_TO_SSH_KEY parameter. In this case '
                    'the key pair will be created automatically. Also to key '
                    'pair ID will be added little ID (8 characters (letters '
                    'and/or digits)) for its uniqueness. In the end of tests '
                    'key pair will be deleted.'),
    cfg.StrOpt('PATH_TO_SSH_KEY',
               help='Path to id_rsa key which is used with tests for remote '
                    'command execution. If you specify wrong path to key '
                    'then you will have the error "Private key file is '
                    'encrypted". Please, make sure you specified right path '
                    'to key. If this parameter is not specified, key pair '
                    '(private and public SSH keys) will be generated '
                    'automatically, using nova client.'),
    cfg.StrOpt('FLOATING_IP_POOL',
               help='Pool name for floating IPs. If Sahara uses Nova '
                    'management network and auto assignment of IPs was '
                    'enabled then you should leave default value of this '
                    'parameter. If auto assignment was not enabled, then you '
                    'should specify value (floating IP pool name) of this '
                    'parameter. If Sahara uses Neutron management network, '
                    'then you should always specify value (floating IP pool '
                    'name) of this parameter.'),
    cfg.BoolOpt('NEUTRON_ENABLED',
                default=False,
                help='If Sahara uses Nova management network, then you '
                     'should leave default value of this flag. If Sahara '
                     'uses Neutron management network, then you should set '
                     'this flag to True and specify values of the following '
                     'parameters: FLOATING_IP_POOL and '
                     'INTERNAL_NEUTRON_NETWORK.'),
    cfg.StrOpt('INTERNAL_NEUTRON_NETWORK',
               default='private',
               help='Name for internal Neutron network.'),
    cfg.BoolOpt('RETAIN_CLUSTER_AFTER_TEST',
                default=False,
                help='If this flag is True, the cluster and related '
                     'objects will not be deleted after the test. '
                     'This is intended as a debugging aid when '
                     'running integration tests on local hosts.'),
    cfg.BoolOpt('RETAIN_EDP_AFTER_TEST',
                default=False,
                help='If this flag is True, the EDP jobs and related '
                     'objects will not be deleted after the test. '
                     'This is intended as a debugging aid when '
                     'running integration tests on local hosts.')
]


VANILLA_CONFIG_GROUP = cfg.OptGroup(name='VANILLA')
VANILLA_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='vanilla',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='1.2.1',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='hadoop',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/usr/share/hadoop/hadoop-examples-1.2.1.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/mnt/log/hadoop/hadoop/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/volumes/disk1/log/hadoop/hadoop/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'jobtracker': 50030,
                    'namenode': 50070,
                    'tasktracker': 50060,
                    'datanode': 50075,
                    'secondarynamenode': 50090,
                    'oozie': 11000
                },
                help='Hadoop process map with ports for Vanilla plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'namenode',
                    'tt': 'tasktracker',
                    'dn': 'datanode'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for Vanilla plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False)
]


VANILLA_TWO_CONFIG_GROUP = cfg.OptGroup(name='VANILLA_TWO')
VANILLA_TWO_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='vanilla',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='2.4.1',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='hadoop',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/opt/hadoop/share/hadoop/mapreduce/'
                       'hadoop-mapreduce-examples-2.4.1.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/mnt/yarn/logs/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/volumes/disk1/yarn/logs/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'resourcemanager': 8088,
                    'namenode': 50070,
                    'nodemanager': 8042,
                    'datanode': 50075
                },
                help='Hadoop process map with ports for Vanilla plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'namenode',
                    'tt': 'nodemanager',
                    'dn': 'datanode'
                },
                help='Names for namenode, nodemanager and datanode '
                     'processes.'),
    cfg.ListOpt('SKIP_EDP_JOB_TYPES',
                default=[],
                help='List of skipped EDP job types.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for Vanilla plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False)
]

CDH_CONFIG_GROUP = cfg.OptGroup(name='CDH')
CDH_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='cdh',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               default=None,
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               default=None,
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               default=None,
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='5.3.0',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='hdfs',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/usr/lib/hadoop-mapreduce'
               '/hadoop-mapreduce-examples.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.StrOpt('CDH_REPO_LIST_URL',
               default='http://archive-primary.cloudera.com/cdh5/ubuntu'
                       '/precise/amd64/cdh/cloudera.list'),
    cfg.StrOpt('CM_REPO_LIST_URL',
               default='http://archive-primary.cloudera.com/cm5/ubuntu'
                       '/precise/amd64/cm/cloudera.list'),
    cfg.StrOpt('CDH_APT_KEY_URL',
               default='http://archive-primary.cloudera.com/cdh5/ubuntu'
                       '/precise/amd64/cdh/archive.key'),
    cfg.StrOpt('CM_APT_KEY_URL',
               default='http://archive-primary.cloudera.com/cm5/ubuntu'
                       '/precise/amd64/cm/archive.key'),
    cfg.StrOpt('MANAGERNODE_FLAVOR',
               default='3',
               help='Id of flavor for manager-node'),
    cfg.StrOpt('LARGE_FLAVOR',
               default='4',
               help='Id of flavor for services-node'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'YARN_RESOURCEMANAGER': 8088,
                    'HDFS_NAMENODE': 50070,
                    'HDFS_SECONDARYNAMENODE': 50090,
                    'YARN_NODEMANAGER': 8042,
                    'HDFS_DATANODE': 50075,
                    'CLOUDERA_MANAGER': 7180,
                    'YARN_JOBHISTORY': 19888,
                    'OOZIE_SERVER': 11000
                },
                help='Hadoop process map with ports for CDH plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'HDFS_NAMENODE',
                    'tt': 'YARN_NODEMANAGER',
                    'dn': 'HDFS_DATANODE'
                },
                help='Names for namenode, nodemanager and datanode '
                     'processes.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for CDH plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False),
    cfg.BoolOpt('SKIP_CHECK_SERVICES_TEST', default=True)
]


HDP_CONFIG_GROUP = cfg.OptGroup(name='HDP')
HDP_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='hdp',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related '
                    'parameters, then image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.ListOpt('MASTER_NODE_PROCESSES',
                default=['JOBTRACKER', 'NAMENODE', 'SECONDARY_NAMENODE',
                         'GANGLIA_SERVER', 'NAGIOS_SERVER',
                         'AMBARI_SERVER', 'OOZIE_SERVER'],
                help='A list of processes that will be launched '
                     'on master node'),
    cfg.ListOpt('WORKER_NODE_PROCESSES',
                default=['TASKTRACKER', 'DATANODE', 'HDFS_CLIENT',
                         'MAPREDUCE_CLIENT', 'OOZIE_CLIENT', 'PIG'],
                help='A list of processes that will be launched '
                     'on worker nodes'),
    cfg.StrOpt('HADOOP_VERSION',
               default='1.3.2',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='hdfs',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/usr/lib/hadoop/hadoop-examples.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/mnt/hadoop/mapred/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/volumes/disk1/hadoop/mapred/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.IntOpt('SCALE_EXISTING_NG_COUNT',
               default=1,
               help='The number of hosts to add while scaling '
                    'an existing node group.'),
    cfg.IntOpt('SCALE_NEW_NG_COUNT',
               default=1,
               help='The number of hosts to add while scaling '
                    'a new node group.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'JOBTRACKER': 50030,
                    'NAMENODE': 50070,
                    'TASKTRACKER': 50060,
                    'DATANODE': 50075,
                    'SECONDARY_NAMENODE': 50090,
                    'OOZIE_SERVER': 11000
                },
                help='Hadoop process map with ports for HDP plugin.'
                ),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'NAMENODE',
                    'tt': 'TASKTRACKER',
                    'dn': 'DATANODE'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for HDP plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False)
]

HDP2_CONFIG_GROUP = cfg.OptGroup(name='HDP2')
HDP2_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='hdp',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               default=None,
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related '
                    'parameters, then image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               default=None,
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               default=None,
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.ListOpt('MASTER_NODE_PROCESSES',
                default=['NAMENODE', 'SECONDARY_NAMENODE', 'ZOOKEEPER_SERVER',
                         'AMBARI_SERVER', 'HISTORYSERVER', 'RESOURCEMANAGER',
                         'GANGLIA_SERVER', 'NAGIOS_SERVER', 'OOZIE_SERVER'],
                help='A list of processes that will be launched '
                     'on master node'),
    cfg.ListOpt('WORKER_NODE_PROCESSES',
                default=['HDFS_CLIENT', 'DATANODE', 'ZOOKEEPER_CLIENT',
                         'MAPREDUCE2_CLIENT', 'YARN_CLIENT', 'NODEMANAGER',
                         'PIG', 'OOZIE_CLIENT'],
                help='A list of processes that will be launched '
                     'on worker nodes'),
    cfg.StrOpt('HADOOP_VERSION',
               default='2.0.6',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='hdfs',
               help='Username which is used for access to Hadoop services.'),
    cfg.IntOpt('SCALE_EXISTING_NG_COUNT',
               default=1,
               help='The number of hosts to add while scaling '
                    'an existing node group.'),
    cfg.IntOpt('SCALE_NEW_NG_COUNT',
               default=1,
               help='The number of hosts to add while scaling '
                    'a new node group.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'RESOURCEMANAGER': 8088,
                    'NAMENODE': 8020,
                    'HISTORYSERVER': 19888,
                    'SECONDARY_NAMENODE': 50090,
                    'OOZIE_SERVER': 11000
                },
                help='Hadoop process map with ports for HDP plugin.'
                ),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'NAMENODE',
                    'tt': 'NODEMANAGER',
                    'dn': 'DATANODE'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for HDP plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False)
]


SPARK_CONFIG_GROUP = cfg.OptGroup(name='SPARK')
SPARK_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='spark',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               default=None,
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related '
                    'parameters, then image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               default=None,
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               default=None,
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.ListOpt('MASTER_NODE_PROCESSES',
                default=['namenode', 'master'],
                help='A list of processes that will be launched '
                     'on master node'),
    cfg.ListOpt('WORKER_NODE_PROCESSES',
                default=['datanode', 'slave'],
                help='A list of processes that will be launched '
                     'on worker nodes'),
    cfg.StrOpt('HADOOP_VERSION',
               default='1.0.0',
               help='Version of Spark (even though it says "HADOOP".'),
    cfg.StrOpt('HADOOP_USER',
               default='hdfs',
               help='Username which is used for access to Hadoop services.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'master': 7077,
                    'namenode': 8020,
                    'datanode': 50075
                },
                help='Spark process map with ports for spark plugin.'
                ),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'namenode',
                    'tt': 'tasktracker',
                    'dn': 'datanode'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for Spark plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False)
]


MAPR_311_CONFIG_GROUP = cfg.OptGroup(name='MAPR_311')
MAPR_311_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='mapr',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='3.1.1',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='mapr',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/opt/mapr/hadoop/hadoop-0.20.2/'
                       'hadoop-0.20.2-dev-examples.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/opt/mapr/hadoop/hadoop-0.20.2/logs/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/opt/mapr/hadoop/hadoop-0.20.2/logs/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'JobTracker': 50030,
                    'CLDB': 7221,
                    'TaskTracker': 50060,
                    'Oozie': 11000
                },
                help='Hadoop process map with ports for MapR plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'CLDB',
                    'tt': 'TaskTracker',
                    'dn': 'FileServer'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.ListOpt('SKIP_EDP_JOB_TYPES',
                default=[],
                help='List of skipped EDP job types.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for MapR plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False),
    cfg.BoolOpt('SKIP_DECOMISSION_TEST', default=False),
]


MAPR_401MRV1_CONFIG_GROUP = cfg.OptGroup(name='MAPR_401MRV1')
MAPR_401MRV1_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='mapr',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='4.0.1.mrv1',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='mapr',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/opt/mapr/hadoop/hadoop-0.20.2/'
                       'hadoop-0.20.2-dev-examples.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/opt/mapr/hadoop/hadoop-0.20.2/logs/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/opt/mapr/hadoop/hadoop-0.20.2/logs/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'JobTracker': 50030,
                    'CLDB': 7221,
                    'TaskTracker': 50060,
                    'Oozie': 11000
                },
                help='Hadoop process map with ports for MapR plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'CLDB',
                    'tt': 'TaskTracker',
                    'dn': 'FileServer'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.ListOpt('SKIP_EDP_JOB_TYPES',
                default=[],
                help='List of skipped EDP job types.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for MapR plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False),
    cfg.BoolOpt('SKIP_DECOMISSION_TEST', default=False),
]


MAPR_401MRV2_CONFIG_GROUP = cfg.OptGroup(name='MAPR_401MRV2')
MAPR_401MRV2_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='mapr',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='4.0.1.mrv2',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='mapr',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/opt/mapr/hadoop/hadoop-2.4.1/share/hadoop/mapreduce'
                       '/hadoop-mapreduce-examples-2.4.1-mapr-1408.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/opt/mapr/hadoop/hadoop-2.4.1/logs/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/opt/mapr/hadoop/hadoop-2.4.1/logs/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'ResourceManager': 8088,
                    'CLDB': 7221,
                    'NodeManager': 8042,
                    'Oozie': 11000
                },
                help='Hadoop process map with ports for MapR plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'CLDB',
                    'tt': 'NodeManager',
                    'dn': 'FileServer'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.ListOpt('SKIP_EDP_JOB_TYPES',
                default=[],
                help='List of skipped EDP job types.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for MapR plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False),
    cfg.BoolOpt('SKIP_DECOMISSION_TEST', default=False),
]


MAPR_402MRV1_CONFIG_GROUP = cfg.OptGroup(name='MAPR_402MRV1')
MAPR_402MRV1_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='mapr',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='4.0.2.mrv1',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='mapr',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/opt/mapr/hadoop/hadoop-0.20.2/'
                       'hadoop-0.20.2-dev-examples.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/opt/mapr/hadoop/hadoop-0.20.2/logs/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/opt/mapr/hadoop/hadoop-0.20.2/logs/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'JobTracker': 50030,
                    'CLDB': 7221,
                    'TaskTracker': 50060,
                    'Oozie': 11000
                },
                help='Hadoop process map with ports for MapR plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'CLDB',
                    'tt': 'TaskTracker',
                    'dn': 'FileServer'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.ListOpt('SKIP_EDP_JOB_TYPES',
                default=[],
                help='List of skipped EDP job types.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for MapR plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False),
    cfg.BoolOpt('SKIP_DECOMISSION_TEST', default=False),
]


MAPR_402MRV2_CONFIG_GROUP = cfg.OptGroup(name='MAPR_402MRV2')
MAPR_402MRV2_CONFIG_OPTS = [
    cfg.StrOpt('PLUGIN_NAME',
               default='mapr',
               help='Name of plugin.'),
    cfg.StrOpt('IMAGE_ID',
               help='ID for image which is used for cluster creation. Also '
                    'you can specify image name or tag of image instead of '
                    'image ID. If you do not specify image related parameters '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_NAME',
               help='Name for image which is used for cluster creation. Also '
                    'you can specify image ID or tag of image instead of '
                    'image name. If you do not specify image related '
                    'parameters, then the image for cluster creation will be '
                    'chosen by tag "sahara_i_tests".'),
    cfg.StrOpt('IMAGE_TAG',
               help='Tag for image which is used for cluster creation. Also '
                    'you can specify image ID or image name instead of tag of '
                    'image. If you do not specify image related parameters, '
                    'then image for cluster creation will be chosen by '
                    'tag "sahara_i_tests".'),
    cfg.StrOpt('HADOOP_VERSION',
               default='4.0.2.mrv2',
               help='Version of Hadoop.'),
    cfg.StrOpt('HADOOP_USER',
               default='mapr',
               help='Username which is used for access to Hadoop services.'),
    cfg.StrOpt('HADOOP_EXAMPLES_JAR_PATH',
               default='/opt/mapr/hadoop/hadoop-2.5.1/share/hadoop/mapreduce'
                       '/hadoop-mapreduce-examples-2.5.1-mapr-1501.jar',
               help='Path to hadoop examples jar file.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/opt/mapr/hadoop/hadoop-2.5.1/logs/userlogs',
               help='Directory where logs of completed jobs are located.'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY_ON_VOLUME',
               default='/opt/mapr/hadoop/hadoop-2.5.1/logs/userlogs',
               help='Directory where logs of completed jobs on volume mounted '
                    'to node are located.'),
    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                    'ResourceManager': 8088,
                    'CLDB': 7221,
                    'NodeManager': 8042,
                    'Oozie': 11000
                },
                help='Hadoop process map with ports for MapR plugin.'),
    cfg.DictOpt('PROCESS_NAMES',
                default={
                    'nn': 'CLDB',
                    'tt': 'NodeManager',
                    'dn': 'FileServer'
                },
                help='Names for namenode, tasktracker and datanode '
                     'processes.'),
    cfg.ListOpt('SKIP_EDP_JOB_TYPES',
                default=[],
                help='List of skipped EDP job types.'),
    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this flag is True, then all tests for MapR plugin '
                     'will be skipped.'),
    cfg.BoolOpt('SKIP_CINDER_TEST', default=False),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False),
    cfg.BoolOpt('SKIP_DECOMISSION_TEST', default=False),
]


def register_config(config, config_group, config_opts):
    config.register_group(config_group)
    config.register_opts(config_opts, config_group)


@singleton
class ITConfig(object):
    def __init__(self):
        config = 'itest.conf'
        config_files = []
        config_path = '%s/sahara/tests/integration/configs/%s'
        if not os.path.exists(config_path % (os.getcwd(), config)):
            message = ('\n**************************************************'
                       '\nINFO: Configuration file "%s" not found  *\n'
                       '**************************************************'
                       % config)
            print(message, file=sys.stderr)

        else:
            config = os.path.join(
                config_path % (os.getcwd(), config)
            )
            config_files.append(config)

        register_config(cfg.CONF, COMMON_CONFIG_GROUP, COMMON_CONFIG_OPTS)
        register_config(cfg.CONF, VANILLA_CONFIG_GROUP, VANILLA_CONFIG_OPTS)
        register_config(cfg.CONF, CDH_CONFIG_GROUP, CDH_CONFIG_OPTS)
        register_config(cfg.CONF, HDP_CONFIG_GROUP, HDP_CONFIG_OPTS)
        register_config(cfg.CONF, HDP2_CONFIG_GROUP, HDP2_CONFIG_OPTS)
        register_config(
            cfg.CONF, VANILLA_TWO_CONFIG_GROUP, VANILLA_TWO_CONFIG_OPTS)
        register_config(cfg.CONF, SPARK_CONFIG_GROUP, SPARK_CONFIG_OPTS)
        register_config(cfg.CONF, MAPR_311_CONFIG_GROUP, MAPR_311_CONFIG_OPTS)
        register_config(
            cfg.CONF, MAPR_401MRV1_CONFIG_GROUP, MAPR_401MRV1_CONFIG_OPTS)
        register_config(
            cfg.CONF, MAPR_401MRV2_CONFIG_GROUP, MAPR_401MRV2_CONFIG_OPTS)
        register_config(
            cfg.CONF, MAPR_402MRV1_CONFIG_GROUP, MAPR_402MRV1_CONFIG_OPTS)
        register_config(
            cfg.CONF, MAPR_402MRV2_CONFIG_GROUP, MAPR_402MRV2_CONFIG_OPTS)

        cfg.CONF(
            [], project='Sahara_integration_tests',
            default_config_files=config_files
        )

        self.common_config = cfg.CONF.COMMON
        self.vanilla_config = cfg.CONF.VANILLA
        self.vanilla_two_config = cfg.CONF.VANILLA_TWO
        self.cdh_config = cfg.CONF.CDH
        self.hdp_config = cfg.CONF.HDP
        self.hdp2_config = cfg.CONF.HDP2
        self.spark_config = cfg.CONF.SPARK
        self.mapr_311_config = cfg.CONF.MAPR_311
        self.mapr_401mrv1_config = cfg.CONF.MAPR_401MRV1
        self.mapr_401mrv2_config = cfg.CONF.MAPR_401MRV2
        self.mapr_402mrv1_config = cfg.CONF.MAPR_402MRV1
        self.mapr_402mrv2_config = cfg.CONF.MAPR_402MRV2
