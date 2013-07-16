# Copyright (c) 2013 Hortonworks, Inc.
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

import os
from savanna.plugins.hdp import ambariplugin as ap
from savanna.plugins.hdp import clusterspec as cs
import unittest2


class AmbariPluginTest(unittest2.TestCase):
    def test_get_node_processes(self):
        plugin = ap.AmbariPlugin()
        #TODO(jspeidel): provide meaningful input
        service_components = plugin.get_node_processes(1)

        self.assertEqual(5, len(service_components))
        components = service_components['HDFS']
        self.assertIn('NAMENODE', components)
        self.assertIn('DATANODE', components)
        self.assertIn('SECONDARY_NAMENODE', components)
        self.assertIn('HDFS_CLIENT', components)

        components = service_components['MAPREDUCE']
        self.assertIn('JOBTRACKER', components)
        self.assertIn('TASKTRACKER', components)
        self.assertIn('MAPREDUCE_CLIENT', components)

        components = service_components['GANGLIA']
        self.assertIn('GANGLIA_SERVER', components)
        self.assertIn('GANGLIA_MONITOR', components)

        components = service_components['NAGIOS']
        self.assertIn('NAGIOS_SERVER', components)

        components = service_components['AMBARI']
        self.assertIn('AMBARI_SERVER', components)
        self.assertIn('AMBARI_AGENT', components)

    def test_convert(self):
        plugin = ap.AmbariPlugin()
        cluster = TestCluster()
        plugin.convert(cluster,
                       os.path.join(os.path.realpath('../plugins'), 'hdp',
                                    'resources',
                                    'default-cluster.template'))

        with open(os.path.join(os.path.realpath('../plugins'), 'hdp',
                               'resources',
                               'default-cluster.template'), 'r') as f:
            normalized_config = cs.ClusterSpec(f.read()).normalize()

        self.assertEquals(normalized_config.hadoop_version,
                          cluster.hadoop_version)
        self.assertEquals(len(normalized_config.node_groups),
                          len(cluster.node_groups))
        self.assertEquals(len(normalized_config.cluster_configs),
                          len(cluster.cluster_configs))
        #TODO(jspeidel): drill down into node_groups and cluster_configs

    def test_update_infra(self):
        plugin = ap.AmbariPlugin()
        cluster = TestCluster()
        plugin.update_infra(cluster)

        for node_group in cluster.node_groups:
            self.assertEquals(cluster.default_image_id, node_group.image)

    def test_get_configs(self):
        plugin = ap.AmbariPlugin()
        configs = plugin.get_configs("1.1.2")
        self.assertEqual(612, len(configs),
                         "wrong number of configuration properties")


class TestCluster:
    def __init__(self):
        self.hadoop_version = None
        self.cluster_configs = []
        self.node_groups = []
        self.default_image_id = '11111'
