# Copyright (c) 2015 Mirantis Inc.
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

from sahara.plugins.cdh import plugin_utils as pu
from sahara.tests.unit import base as b


CONFIGURATION_SCHEMA = {
    'node_configs': {
        'yarn.scheduler.minimum-allocation-mb': (
            'RESOURCEMANAGER', 'yarn_scheduler_minimum_allocation_mb'),
        'mapreduce.reduce.memory.mb': (
            'YARN_GATEWAY', 'mapreduce_reduce_memory_mb'),
        'mapreduce.map.memory.mb': (
            'YARN_GATEWAY', 'mapreduce_map_memory_mb',),
        'yarn.scheduler.maximum-allocation-mb': (
            'RESOURCEMANAGER', 'yarn_scheduler_maximum_allocation_mb'),
        'yarn.app.mapreduce.am.command-opts': (
            'YARN_GATEWAY', 'yarn_app_mapreduce_am_command_opts'),
        'yarn.nodemanager.resource.memory-mb': (
            'NODEMANAGER', 'yarn_nodemanager_resource_memory_mb'),
        'mapreduce.task.io.sort.mb': (
            'YARN_GATEWAY', 'io_sort_mb'),
        'mapreduce.map.java.opts': (
            'YARN_GATEWAY', 'mapreduce_map_java_opts'),
        'mapreduce.reduce.java.opts': (
            'YARN_GATEWAY', 'mapreduce_reduce_java_opts'),
        'yarn.app.mapreduce.am.resource.mb': (
            'YARN_GATEWAY', 'yarn_app_mapreduce_am_resource_mb')
    },
    'cluster_configs': {
        'dfs.replication': ('HDFS', 'dfs_replication')
    }
}


class TestPluginUtils(b.SaharaTestCase):
    @mock.patch('sahara.plugins.cdh.plugin_utils.'
                'CDHPluginAutoConfigsProvider')
    def test_recommend_configs(self, provider):
        plug_utils = pu.AbstractPluginUtils()
        fake_plugin_utils = mock.Mock()
        fake_cluster = mock.Mock()
        plug_utils.recommend_configs(fake_cluster, fake_plugin_utils, False)
        self.assertEqual([
            mock.call(CONFIGURATION_SCHEMA,
                      fake_plugin_utils, fake_cluster, False)
        ], provider.call_args_list)
