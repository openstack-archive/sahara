# Copyright (c) 2014 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function

import os

from oslo.config import cfg


def class_wrapper(cls):
    instances = {}

    def get_instance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]

    return get_instance


data_processing_group = cfg.OptGroup(name='data_processing',
                                     title='Data Processing options')
DataProcessingGroup = [
    cfg.IntOpt('cluster_timeout',
               default=3600,
               help='Timeout (in seconds) to wait for cluster deployment.'),
    cfg.IntOpt('request_timeout',
               default=10,
               help='Timeout (in seconds) between status checks.'),
    cfg.StrOpt('floating_ip_pool',
               help='Name of IP pool.'),
    cfg.StrOpt('private_network',
               help='Name of the private network '
                    'that provides internal connectivity.'),
    cfg.StrOpt('fake_image_id',
               help='ID of an image which is used for cluster creation.'),
    cfg.StrOpt('flavor_id',
               help='ID of a flavor.'),
    cfg.StrOpt('saharaclient_version',
               default='1.1',
               help='Version of python-saharaclient'),
    cfg.StrOpt('sahara_url',
               help='Sahara url as http://ip:port/api_version/tenant_id'),
    cfg.StrOpt('ssh_username',
               help='Username which is used to log into remote nodes via SSH.')
]


@class_wrapper
class SaharaTestConfig(object):
    DEFAULT_CONFIG_DIR = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'etc')

    DEFAULT_CONFIG_FILE = 'sahara_tests.conf'

    def __init__(self):
        config_files = []
        path = os.path.join(self.DEFAULT_CONFIG_DIR, self.DEFAULT_CONFIG_FILE)
        if os.path.isfile(path):
            config_files.append(path)

        conf = cfg.ConfigOpts()
        conf([], project='Sahara-tests',
             default_config_files=config_files)
        conf.register_group(data_processing_group)
        conf.register_opts(DataProcessingGroup, data_processing_group)

        self.data_processing = conf.data_processing


SAHARA_TEST_CONF = SaharaTestConfig()
