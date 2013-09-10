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

_CONF = importutils.try_import(
    'savanna.tests.integration.configs.common_config')


def _get_conf(key, default):
    return getattr(_CONF, key) if _CONF and hasattr(_CONF, key) else default

OS_USERNAME = _get_conf('OS_USERNAME', 'admin')
OS_PASSWORD = _get_conf('OS_PASSWORD', 'admin')
OS_TENANT_NAME = _get_conf('OS_TENANT_NAME', 'admin')
OS_AUTH_URL = _get_conf('OS_AUTH_URL', 'http://127.0.0.1:35357/v2.0/')

SAVANNA_HOST = _get_conf('SAVANNA_HOST', '127.0.0.1')
SAVANNA_PORT = _get_conf('SAVANNA_PORT', '8386')

FLAVOR_ID = _get_conf('FLAVOR_ID', '2')

TIMEOUT = _get_conf('TIMEOUT', 45)

CLUSTER_NAME = _get_conf('CLUSTER_NAME', 'test-cluster')

USER_KEYPAIR_ID = _get_conf('USER_KEYPAIR_ID', 'jenkins')

PATH_TO_SSH = _get_conf('PATH_TO_SSH', '/home/ubuntu/.ssh/id_rsa')

JT_PORT = _get_conf('JT_PORT', 50030)
NN_PORT = _get_conf('NN_PORT', 50070)
TT_PORT = _get_conf('TT_PORT', 50060)
DN_PORT = _get_conf('DN_PORT', 50075)
SEC_NN_PORT = _get_conf('SEC_NN_PORT', 50090)

ENABLE_CLUSTER_CL_TEMPLATE_CRUD_TESTS = _get_conf(
    'ENABLE_CLUSTER_CL_TEMPLATE_CRUD_TESTS', True)
ENABLE_CLUSTER_NGT_NODE_PROCESS_CRUD_TESTS = _get_conf(
    'ENABLE_CLUSTER_NGT_NODE_PROCESS_CRUD_TESTS', True)
ENABLE_CLUSTER_NGT_CRUD_TESTS = _get_conf(
    'ENABLE_CLUSTER_NGT_CRUD_TESTS', True)
ENABLE_CLUSTER_NODE_PROCESS_CRUD_TESTS = _get_conf(
    'ENABLE_CLUSTER_NODE_PROCESS_CRUD_TESTS', True)

ENABLE_CL_TEMPLATE_CRUD_TESTS = _get_conf(
    'ENABLE_CL_TEMPLATE_CRUD_TESTS', True)
ENABLE_NGT_CRUD_TESTS = _get_conf('ENABLE_NGT_CRUD_TESTS', True)

ENABLE_HADOOP_TESTS_FOR_VANILLA_PLUGIN = _get_conf(
    'ENABLE_HADOOP_TESTS_FOR_VANILLA_PLUGIN', True)
ENABLE_HADOOP_TESTS_FOR_HDP_PLUGIN = _get_conf(
    'ENABLE_HADOOP_TESTS_FOR_HDP_PLUGIN', True)
ENABLE_SWIFT_TESTS = _get_conf('ENABLE_SWIFT_TESTS', True)
ENABLE_SCALING_TESTS = _get_conf('ENABLE_SCALING_TESTS', True)
ENABLE_CONFIG_TESTS = _get_conf('ENABLE_CONFIG_TESTS', True)

ENABLE_IR_TESTS = _get_conf('ENABLE_IR_TESTS', True)
