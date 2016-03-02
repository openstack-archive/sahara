# Copyright (c) 2015 Intel Corporation.
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

import mock

from sahara.plugins.cdh.v5 import plugin_utils as pu
from sahara.tests.unit.plugins.cdh import base_plugin_utils_test


class TestPluginUtilsV5(base_plugin_utils_test.TestPluginUtils):

    def setUp(self):
        super(TestPluginUtilsV5, self).setUp()
        self.plug_utils = pu.PluginUtilsV5()
        self.version = "v5"

    @mock.patch('sahara.config.CONF.disable_event_log')
    def test_create_hive_hive_directory(self, log_cfg):
        cluster = base_plugin_utils_test.get_concrete_cluster()
        namenode = cluster.node_groups[1].instances[0]
        self.plug_utils.create_hive_hive_directory(cluster)
        with namenode.remote() as r:
            calls = [mock.call('sudo su - -c "hadoop fs -mkdir -p'
                               ' /tmp/hive-hive" hdfs'),
                     mock.call('sudo su - -c "hadoop fs -chown hive'
                               ' /tmp/hive-hive" hdfs')]
            r.execute_command.assert_has_calls(calls, any_order=False)
