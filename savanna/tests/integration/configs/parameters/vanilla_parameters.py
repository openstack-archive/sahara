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
    'savanna.tests.integration.configs.vanilla_config')


def _get_conf(key, default):
    return getattr(_CONF, key) if _CONF and hasattr(_CONF, key) else default

PLUGIN_NAME = _get_conf('PLUGIN_NAME', 'vanilla')

IMAGE_ID = _get_conf('IMAGE_ID', 'b244500e-583a-434f-a40f-6ba87fd55e09')

NODE_USERNAME = _get_conf('NODE_USERNAME', 'ubuntu')

HADOOP_VERSION = _get_conf('HADOOP_VERSION', '1.1.2')
HADOOP_USER = _get_conf('HADOOP_USER', 'hadoop')
HADOOP_DIRECTORY = _get_conf('HADOOP_DIRECTORY', '/usr/share/hadoop')
HADOOP_LOG_DIRECTORY = _get_conf('HADOOP_LOG_DIRECTORY',
                                 '/mnt/log/hadoop/hadoop/userlogs')
