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

from sahara.plugins.vanilla.hadoop2 import config as c
from sahara.tests.unit import base


class VanillaTwoConfigTestCase(base.SaharaTestCase):
    def test_get_hadoop_dirs(self):
        ng = FakeNG(storage_paths=['/vol1', '/vol2'])
        dirs = c._get_hadoop_dirs(ng)
        expected = {
            'hadoop_name_dirs': ['/vol1/hdfs/namenode',
                                 '/vol2/hdfs/namenode'],
            'hadoop_data_dirs': ['/vol1/hdfs/datanode',
                                 '/vol2/hdfs/datanode'],
            'hadoop_log_dir': '/vol1/hadoop/logs',
            'hadoop_secure_dn_log_dir': '/vol1/hadoop/logs/secure',
            'yarn_log_dir': '/vol1/yarn/logs'
        }
        self.assertEqual(expected, dirs)


class FakeNG(object):
    def __init__(self, storage_paths=None):
        self.paths = storage_paths

    def storage_paths(self):
        return self.paths
