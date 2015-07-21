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
import testtools

from sahara.plugins.vanilla.hadoop2 import recommendations_utils as ru

CONFIGURATION_SCHEMA = {
    'cluster_configs': {
        'dfs.replication': ('HDFS', 'dfs.replication')
    },
    'node_configs': {
        'yarn.app.mapreduce.am.command-opts': (
            'MapReduce', 'yarn.app.mapreduce.am.command-opts'),
        'yarn.scheduler.maximum-allocation-mb': (
            'YARN', 'yarn.scheduler.maximum-allocation-mb'),
        'yarn.app.mapreduce.am.resource.mb': (
            'MapReduce', 'yarn.app.mapreduce.am.resource.mb'),
        'yarn.scheduler.minimum-allocation-mb': (
            'YARN', 'yarn.scheduler.minimum-allocation-mb'),
        'yarn.nodemanager.vmem-check-enabled': (
            'YARN', 'yarn.nodemanager.vmem-check-enabled'),
        'mapreduce.map.java.opts': (
            'MapReduce', 'mapreduce.map.java.opts'),
        'mapreduce.reduce.memory.mb': (
            'MapReduce', 'mapreduce.reduce.memory.mb'),
        'yarn.nodemanager.resource.memory-mb': (
            'YARN', 'yarn.nodemanager.resource.memory-mb'),
        'mapreduce.reduce.java.opts': (
            'MapReduce', 'mapreduce.reduce.java.opts'),
        'mapreduce.map.memory.mb': (
            'MapReduce', 'mapreduce.map.memory.mb'),
        'mapreduce.task.io.sort.mb': (
            'MapReduce', 'mapreduce.task.io.sort.mb')
    }
}


class TestVersionHandler(testtools.TestCase):
    @mock.patch('sahara.plugins.recommendations_utils.'
                'HadoopAutoConfigsProvider')
    def test_recommend_configs(self, provider):
        f_cluster, f_configs = mock.Mock(), mock.Mock()
        ru.recommend_configs(f_cluster, f_configs, False)
        self.assertEqual([
            mock.call(CONFIGURATION_SCHEMA, f_configs, f_cluster, False)
        ], provider.call_args_list)
