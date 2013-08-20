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

_CONF = importutils.try_import('savanna.tests.integration.configs.hdp_config')


def _get_conf(key, default):
    return getattr(_CONF, key) if _CONF and hasattr(_CONF, key) else default

PLUGIN_NAME = _get_conf('PLUGIN_NAME', 'hdp')

IMAGE_ID = _get_conf('IMAGE_ID', '5ea141c3-893e-4b5c-b138-910adc09b281')

NODE_USERNAME = _get_conf('NODE_USERNAME', 'cloud-user')

HADOOP_VERSION = _get_conf('HADOOP_VERSION', '1.3.0')
HADOOP_USER = _get_conf('HADOOP_USER', 'hdfs')
HADOOP_DIRECTORY = _get_conf('HADOOP_DIRECTORY', '/usr/lib/hadoop')
HADOOP_LOG_DIRECTORY = _get_conf('HADOOP_LOG_DIRECTORY',
                                 '/hadoop/mapred/userlogs')
