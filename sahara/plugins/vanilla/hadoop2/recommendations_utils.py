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

from sahara.plugins import recommendations_utils as ru


def recommend_configs(cluster, plugin_configs, scaling):
    yarn_configs = [
        'yarn.nodemanager.resource.memory-mb',
        'yarn.scheduler.minimum-allocation-mb',
        'yarn.scheduler.maximum-allocation-mb',
        'yarn.nodemanager.vmem-check-enabled',
    ]
    mapred_configs = [
        'yarn.app.mapreduce.am.resource.mb',
        'yarn.app.mapreduce.am.command-opts',
        'mapreduce.map.memory.mb',
        'mapreduce.reduce.memory.mb',
        'mapreduce.map.java.opts',
        'mapreduce.reduce.java.opts',
        'mapreduce.task.io.sort.mb',
    ]
    configs_to_configure = {
        'cluster_configs': {
            'dfs.replication': ('HDFS', 'dfs.replication')
        },
        'node_configs': {
        }
    }
    for mapr in mapred_configs:
        configs_to_configure['node_configs'][mapr] = ("MapReduce", mapr)
    for yarn in yarn_configs:
        configs_to_configure['node_configs'][yarn] = ('YARN', yarn)
    provider = ru.HadoopAutoConfigsProvider(
        configs_to_configure, plugin_configs, cluster, scaling)
    provider.apply_recommended_configs()
