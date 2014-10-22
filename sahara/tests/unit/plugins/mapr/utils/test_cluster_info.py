# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import sahara.plugins.mapr.util.cluster_info as ci
import sahara.plugins.mapr.util.plugin_spec as ps
import sahara.tests.unit.base as b
import sahara.tests.unit.plugins.mapr.stubs as s


class ClusterInfoTest(b.SaharaTestCase):

    def assertItemsEqual(self, expected, actual):
        for e in expected:
            self.assertIn(e, actual)
        for a in actual:
            self.assertIn(a, expected)

    def setUp(self):
        b.SaharaTestCase.setUp(self)
        path = 'tests/unit/plugins/mapr/utils/resources/plugin_spec_ci.json'
        self.plugin_spec = ps.PluginSpec(path)

    def test_get_node_group_services(self):
        node_processes = ['ZooKeeper', 'Webserver', 'CLDB']
        node_group = s.NodeGroup(None, node_processes=node_processes)
        cluster_info = ci.ClusterInfo(None, self.plugin_spec)
        actual = cluster_info.get_services(node_group)
        expected = ['Management', 'MapR FS', 'general']
        self.assertItemsEqual(expected, actual)

    def test_get_cluster_services(self):
        np0 = ['ZooKeeper', 'Webserver', 'CLDB']
        ng0 = s.NodeGroup(node_processes=np0)
        np1 = ['ZooKeeper', 'TaskTracker', 'FileServer']
        ng1 = s.NodeGroup(node_processes=np1)
        cluster = s.Cluster(node_groups=[ng0, ng1])
        cluster_info = ci.ClusterInfo(cluster, self.plugin_spec)
        actual = cluster_info.get_services()
        expected = ['Management', 'MapR FS', 'general', 'MapReduce']
        self.assertItemsEqual(expected, actual)
