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

import savanna.openstack.common.importutils as importutils

_CONF = importutils.try_import('savanna.tests.integration.configs.config')


def _get_conf(key, default):
    return getattr(_CONF, key) if _CONF and hasattr(_CONF, key) else default

OS_USERNAME = _get_conf('OS_USERNAME', 'admin')
OS_PASSWORD = _get_conf('OS_PASSWORD', 'password')
OS_TENANT_NAME = _get_conf('OS_TENANT_NAME', 'admin')
OS_AUTH_URL = _get_conf('OS_AUTH_URL', 'http://192.168.1.1:35357/v2.0/')

SAVANNA_HOST = _get_conf('SAVANNA_HOST', '192.168.1.1')
SAVANNA_PORT = _get_conf('SAVANNA_PORT', '8386')

IMAGE_ID = _get_conf('IMAGE_ID', '42abc')
FLAVOR_ID = _get_conf('FLAVOR_ID', '42')

NODE_USERNAME = _get_conf('NODE_USERNAME', 'username')

CLUSTER_NAME_CRUD = _get_conf('CLUSTER_NAME_CRUD', 'cluster-crud')
CLUSTER_NAME_HADOOP = _get_conf('CLUSTER_NAME_HADOOP', 'cluster-hadoop')
CLUSTER_NAME_SWIFT = _get_conf('CLUSTER_NAME_SWIFT', 'cluster-swift')

TIMEOUT = _get_conf('TIMEOUT', 15)

HADOOP_VERSION = _get_conf('HADOOP_VERSION', '1.1.2')
HADOOP_DIRECTORY = _get_conf('HADOOP_DIRECTORY', '/usr/share/hadoop')
HADOOP_LOG_DIRECTORY = _get_conf('HADOOP_LOG_DIRECTORY',
                                 '/mnt/log/hadoop/hadoop/userlogs')

SSH_KEY = _get_conf('SSH_KEY', 'jenkins')
PATH_TO_SSH = _get_conf('PATH_TO_SSH', '/home/user/.ssh/id_rsa')

PLUGIN_NAME = _get_conf('PLUGIN_NAME', 'vanilla')

NAMENODE_CONFIG = _get_conf('NAMENODE_CONFIG', {})
JOBTRACKER_CONFIG = _get_conf('JOBTRACKER_CONFIG', {})
DATANODE_CONFIG = _get_conf('DATANODE_CONFIG', {})
TASKTRACKER_CONFIG = _get_conf('TASKTRACKER_CONFIG', {})
GENERAL_CONFIG = _get_conf('GENERAL_CONFIG', {})
CLUSTER_HDFS_CONFIG = _get_conf('CLUSTER_HDFS_CONFIG', {})
CLUSTER_MAPREDUCE_CONFIG = _get_conf('CLUSTER_MAPREDUCE_CONFIG', {})

JT_PORT = _get_conf('JT_PORT', 50030)
NN_PORT = _get_conf('NN_PORT', 50070)
TT_PORT = _get_conf('TT_PORT', 50060)
DN_PORT = _get_conf('DN_PORT', 50075)

ENABLE_SWIFT_TESTS = _get_conf('ENABLE_SWIFT_TESTS', True)
