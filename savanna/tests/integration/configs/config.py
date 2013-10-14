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

from oslo.config import cfg


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
               default='admin', help='Username for OpenStack'),
    cfg.StrOpt('OS_PASSWORD',
               default='admin', help='Password for OpenStack'),
    cfg.StrOpt('OS_TENANT_NAME',
               default='admin', help='Tenant name for OpenStack'),
    cfg.StrOpt('OS_AUTH_URL',
               default='http://127.0.0.1:35357/v2.0/',
               help='URL for OpenStack'),

    cfg.StrOpt('SAVANNA_HOST',
               default='127.0.0.1',
               help='Host for Savanna'),
    cfg.IntOpt('SAVANNA_PORT',
               default=8386,
               help='Port for Savanna'),
    cfg.StrOpt('SAVANNA_API_VERSION',
               default='v1.1',
               help='Api version for Savanna'),

    cfg.StrOpt('FLAVOR_ID',
               default=2,
               help='OpenStack flavor ID for image'),

    cfg.IntOpt('CLUSTER_CREATION_TIMEOUT',
               default=30,
               help='Cluster creation timeout (in minutes); '
                    'minimal value is 1'),

    cfg.IntOpt('TELNET_TIMEOUT',
               default=5,
               help='Timeout for node process deployment on cluster '
                    'nodes (in minutes); minimal value is 1'),

    cfg.IntOpt('HDFS_INITIALIZATION_TIMEOUT',
               default=5,
               help='Timeout for HDFS initialization (in minutes); '
                    'minimal value is 1'),

    cfg.IntOpt('JOB_LAUNCH_TIMEOUT',
               default=5,
               help='Timeout for job launch (in minutes); '
                    'minimal value is 1'),

    cfg.StrOpt('CLUSTER_NAME',
               default='test-cluster', help='Name for cluster'),

    cfg.StrOpt('USER_KEYPAIR_ID',
               default='jenkins',
               help='OpenStack key pair id your SSH public key which '
                    'Savanna transfers to cluster nodes for access of users '
                    'to virtual machines via SSH, using this key'),

    cfg.StrOpt('PATH_TO_SSH_KEY',
               default='/home/ubuntu/.ssh/id_rsa',
               help='Path to id_rsa key which is used with tests for remote '
                    'command execution. For right work of tests you should '
                    'export your public key id_rsa.pub to Open Stack and '
                    'specify its key pair id in configuration file of tests. '
                    'If you specified wrong path to key then you will have '
                    'the error "Private key file is encrypted". Please, make '
                    'sure you specified right path to key')
]


VANILLA_CONFIG_GROUP = cfg.OptGroup(name='VANILLA')
VANILLA_CONFIG_OPTS = [

    cfg.StrOpt('PLUGIN_NAME',
               default='vanilla',
               help='Name of plugin'),

    cfg.StrOpt('IMAGE_ID',
               default='e9691262-e286-46f7-aea5-9f40461b5eea',
               help='ID for image which is used for cluster creation'),

    cfg.StrOpt('NODE_USERNAME',
               default='ubuntu',
               help='Username which is used for connecting to cluster nodes '
                    'via SSH'),

    cfg.StrOpt('HADOOP_VERSION',
               default='1.2.1', help='Version of Hadoop'),
    cfg.StrOpt('HADOOP_USER',
               default='hadoop',
               help='Username which is used for access to Hadoop services'),
    cfg.StrOpt('HADOOP_DIRECTORY',
               default='/usr/share/hadoop',
               help='Directory where are located Hadoop jar files'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/mnt/log/hadoop/hadoop/userlogs',
               help='Directory where is located log info about '
                    'completed jobs'),

    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={'jobtracker': 50030,
                         'namenode': 50070,
                         'tasktracker': 50060,
                         'datanode': 50075,
                         'secondarynamenode': 50090,
                         'oozie': 11000},
                help='Hadoop process map with ports for Vanilla plugin'),

    cfg.DictOpt('PROCESS_NAMES',
                default={'nn': 'namenode',
                         'tt': 'tasktracker',
                         'dn': 'datanode'},
                help='Names for namenode, tasktracker and datanode processes'),

    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=False,
                help='If this variable is True then tests for Vanilla plugin '
                     'will be skipped'),
    cfg.BoolOpt('SKIP_CLUSTER_CONFIG_TEST', default=False),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False),
    cfg.BoolOpt('SKIP_EDP_TEST', default=False),

]


HDP_CONFIG_GROUP = cfg.OptGroup(name='HDP')
HDP_CONFIG_OPTS = [

    cfg.StrOpt('PLUGIN_NAME',
               default='hdp', help='Name of plugin'),

    cfg.StrOpt('IMAGE_ID',
               default='cd63f719-006e-4541-a523-1fed7b91fa8c',
               help='ID for image which is used for cluster creation'),

    cfg.StrOpt('NODE_USERNAME',
               default='root',
               help='Username which is used for connecting to cluster nodes '
                    'via SSH'),

    cfg.StrOpt('HADOOP_VERSION',
               default='1.3.2', help='Version of Hadoop'),
    cfg.StrOpt('HADOOP_USER',
               default='hdfs',
               help='Username which is used for access to Hadoop services'),
    cfg.StrOpt('HADOOP_DIRECTORY',
               default='/usr/lib/hadoop',
               help='Directory where are located Hadoop jar files'),
    cfg.StrOpt('HADOOP_LOG_DIRECTORY',
               default='/hadoop/mapred/userlogs',
               help='Directory where is located log info about '
                    'completed jobs'),

    cfg.DictOpt('HADOOP_PROCESSES_WITH_PORTS',
                default={
                'JOBTRACKER': 50030,
                'NAMENODE': 50070,
                'TASKTRACKER': 50060,
                'DATANODE': 50075,
                'SECONDARY_NAMENODE': 50090
                },
                help='Hadoop process map with ports for HDP plugin'
                ),

    cfg.DictOpt('PROCESS_NAMES',
                default={'nn': 'NAMENODE',
                         'tt': 'TASKTRACKER',
                         'dn': 'DATANODE'},
                help='Names for namenode, tasktracker and datanode processes'),

    cfg.BoolOpt('SKIP_ALL_TESTS_FOR_PLUGIN',
                default=True,
                help='If this variable is True then tests for HDP plugin '
                     'will be skipped'),
    cfg.BoolOpt('SKIP_MAP_REDUCE_TEST', default=False),
    cfg.BoolOpt('SKIP_SWIFT_TEST', default=False),
    cfg.BoolOpt('SKIP_SCALING_TEST', default=False)
]


def register_config(config, config_group, config_opts):

    config.register_group(config_group)
    config.register_opts(config_opts, config_group)


@singleton
class ITConfig:

    def __init__(self):

        config = 'itest.conf'

        config_files = []

        if not os.path.exists(
                '%s/integration/configs/%s' % (os.getcwd(), config)):

            message = '\n**************************************************' \
                      '\nINFO: Configuration file "%s" not found  *\n' \
                      '**************************************************' \
                      % config
            print(RuntimeError(message), file=sys.stderr)

        else:

            config = os.path.join(
                '%s/integration/configs/%s' % (os.getcwd(), config)
            )
            config_files.append(config)

        register_config(cfg.CONF, COMMON_CONFIG_GROUP, COMMON_CONFIG_OPTS)
        register_config(cfg.CONF, VANILLA_CONFIG_GROUP, VANILLA_CONFIG_OPTS)
        register_config(cfg.CONF, HDP_CONFIG_GROUP, HDP_CONFIG_OPTS)

        cfg.CONF([], project='integration_tests',
                 default_config_files=config_files)

        self.common_config = cfg.CONF.COMMON
        self.vanilla_config = cfg.CONF.VANILLA
        self.hdp_config = cfg.CONF.HDP
