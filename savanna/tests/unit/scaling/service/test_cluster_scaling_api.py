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

import mock

import savanna.db.models as m
from savanna.plugins import base
from savanna.plugins.vanilla import exceptions as ex
from savanna.plugins.vanilla import plugin
from savanna.service import api
from savanna.tests.unit import base as models_test_base


def patch_get_ng(test_ng):
    temp_mock = mock.Mock()
    temp_mock.to_object.return_value = test_ng
    mock.patch("savanna.service.api.get_node_group_template",
               return_value=temp_mock).start()


def patch(cluster, test_ng):
    patch_get_ng(test_ng)
    mock.patch("savanna.service.api.get_cluster",
               return_value=cluster).start()
    mock.patch("savanna.plugins.base.PluginManager.get_plugin",
               return_value=plugin.VanillaProvider()).start()


class ClusterScalingApiTest(models_test_base.DbTestCase):
    def init_cluster(self):
        ng_master = m.NodeGroup('ng1', 'test_flavor',
                                ['namenode', 'jobtracker'], 1)
        ng_master.instances = [m.Instance("ng1", "i1", "i1")]
        ng_datanode = m.NodeGroup('ng2', 'test_flavor',
                                  ['datanode'], 3)
        ng_test_nodes = m.NodeGroup('ng3', 'test_flavor',
                                    ['datanode'], 3)

        cluster = m.Cluster("cluster3", "test_tenant",
                            "vanilla", "1.1.2")
        cluster.node_groups = [ng_master, ng_datanode]
        base.setup_plugins()
        return cluster, ng_test_nodes

    def test_scale_cluster_with_adding_node_group(self):
        cluster, ng_tasktracker = self.init_cluster()
        patch(cluster, ng_tasktracker)
        data = {'resize_node_groups': [],
                'add_node_groups': [{'name': 'ng3', 'count': 4,
                                     'node_group_template_id': '1'}]}
        cluster = api.scale_cluster("1", data)
        self.assertEqual(len(cluster.node_groups), 3)

    def test_scale_cluster_with_adding_node_group_with_none_template_id(self):
        cluster, ng_tasktracker = self.init_cluster()
        patch(cluster, ng_tasktracker)
        data = {'resize_node_groups': [],
                'add_node_groups': [{'name': 'ng3', 'count': 4,
                                     'node_group_template_id': None,
                                     'flavor_id': '3',
                                     'node_processes': ['tasktracker']}]}
        cluster = api.scale_cluster("1", data)
        self.assertEqual(len(cluster.node_groups), 3)

    def test_scale_cluster_with_adding_invalid_node_group(self):
        cluster, ng_tasktracker = self.init_cluster()
        patch(cluster, ng_tasktracker)
        data = {'resize_node_groups': [],
                'add_node_groups': [{'name': 'ng3', 'count': 4,
                                     'node_group_template_id': None,
                                     'flavor_id': '3',
                                     'node_processes': ['namenode']}]}
        with self.assertRaises(ex.NodeGroupCannotBeScaled):
            api.scale_cluster("1", data)


class ConstructNgsForScalingApiTest(models_test_base.DbTestCase):
    def test_create_ngs_with_none_template_id(self):
        additional_ng = [{'name': 'ng3', 'count': 4,
                          'node_group_template_id': None,
                          "flavor_id": "1",
                          "node_processes": ["namenode"]}]
        result = api.construct_ngs_for_scaling(additional_ng)
        self.assertEqual(len(result), 1)
        ng = result.keys()[0]
        self.assertEqual(ng.node_processes, ["namenode"])
        self.assertEqual(result[ng], 4)

    def test_create_ngs_with_template_id(self):
        additional_ng = [{'name': 'ng3', 'count': 4,
                          'node_group_template_id': '1'}]
        test_ng = m.NodeGroup("ng3", "f1", ["tasktracker"], 3)
        patch_get_ng(test_ng)
        result = api.construct_ngs_for_scaling(additional_ng)
        self.assertEqual(len(result), 1)
        ng = result.keys()[0]
        self.assertEqual(result[ng], 4)
