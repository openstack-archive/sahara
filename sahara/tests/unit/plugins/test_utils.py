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

from unittest import mock

from sahara.plugins import exceptions as ex
from sahara.plugins import utils as pu
from sahara.tests.unit import base as b


class FakeInstance(object):
    def __init__(self, _id, node_processes=None):
        self.id = _id
        self.node_processes = node_processes or []

    @property
    def node_group(self):
        return self

    def __eq__(self, other):
        return self.id == other.id


class FakeNodeGroup(object):

    def __init__(self, node_processes, instances=None):
        self.node_processes = node_processes
        self.instances = instances or []
        self.count = len(self.instances)

    def __eq__(self, other):
        return self.node_processes == other.node_processes


class TestPluginUtils(b.SaharaTestCase):

    def setUp(self):
        super(TestPluginUtils, self).setUp()
        self.cluster = mock.Mock()
        self.cluster.node_groups = [
            FakeNodeGroup(["node_process1"], [FakeInstance("1")]),
            FakeNodeGroup(["node_process2"], [FakeInstance("2")]),
            FakeNodeGroup(["node_process3"], [FakeInstance("3")]),
        ]

    def test_get_node_groups(self):
        res = pu.get_node_groups(self.cluster)
        self.assertEqual([
            FakeNodeGroup(["node_process1"]),
            FakeNodeGroup(["node_process2"]),
            FakeNodeGroup(["node_process3"]),
        ], res)

        res = pu.get_node_groups(self.cluster, "node_process1")
        self.assertEqual([
            FakeNodeGroup(["node_process1"])
        ], res)

        res = pu.get_node_groups(self.cluster, "node_process")
        self.assertEqual([], res)

    def test_get_instances_count(self):
        res = pu.get_instances_count(self.cluster)
        self.assertEqual(3, res)

        res = pu.get_instances_count(self.cluster, "node_process1")
        self.assertEqual(1, res)

    def test_get_instances(self):
        res = pu.get_instances(self.cluster)
        self.assertEqual([
            FakeInstance("1"), FakeInstance("2"), FakeInstance("3")], res)

        res = pu.get_instances(self.cluster, "node_process1")
        self.assertEqual([FakeInstance("1")], res)

    def test_get_instance(self):
        self.assertRaises(ex.InvalidComponentCountException,
                          pu.get_instance, self.cluster, None)

        res = pu.get_instance(self.cluster, "node_process")
        self.assertIsNone(res)

        res = pu.get_instance(self.cluster, "node_process1")
        self.assertEqual(FakeInstance("1"), res)

    def test_generate_host_names(self):
        node = mock.Mock()
        node.hostname = mock.Mock(return_value="host_name")

        res = pu.generate_host_names([node, node])
        self.assertEqual("host_name\nhost_name", res)

    def test_generate_fqdn_host_names(self):
        node = mock.Mock()
        node.fqdn = mock.Mock(return_value="fqdn")

        res = pu.generate_fqdn_host_names([node, node])
        self.assertEqual("fqdn\nfqdn", res)

    def test_get_port_from_address(self):

        res = pu.get_port_from_address("0.0.0.0:8000")
        self.assertEqual(8000, res)

        res = pu.get_port_from_address("http://localhost:8000/resource")
        self.assertEqual(8000, res)

        res = pu.get_port_from_address("http://192.168.1.101:10000")
        self.assertEqual(10000, res)

        res = pu.get_port_from_address("mydomain")
        self.assertIsNone(res)

    def test_instances_with_services(self):
        inst = [FakeInstance("1", ["nodeprocess1"]),
                FakeInstance("2", ["nodeprocess2"])]

        node_processes = ["nodeprocess"]
        res = pu.instances_with_services(inst, node_processes)
        self.assertEqual([], res)

        node_processes = ["nodeprocess1"]
        res = pu.instances_with_services(inst, node_processes)
        self.assertEqual([FakeInstance("1", ["nodeprocess1"])], res)

    @mock.patch("sahara.plugins.utils.plugins_base")
    def test_get_config_value_or_default(self, mock_plugins_base):
        # no config
        self.assertRaises(RuntimeError,
                          pu.get_config_value_or_default)

        config = mock.Mock()
        config.applicable_target = "service"
        config.name = "name"
        config.default_value = "default_value"

        # cluster has the config
        cluster = mock.Mock()
        cluster.cluster_configs = {"service": {"name": "name"}}
        cluster.plugin_name = "plugin_name"
        cluster.hadoop_version = "hadoop_version"

        res = pu.get_config_value_or_default(cluster=cluster,
                                             config=config)
        self.assertEqual("name", res)

        # node group has the config
        cluster.cluster_configs = {}

        node_group1 = mock.Mock()
        node_group2 = mock.Mock()

        node_group1.configuration = mock.Mock(return_value={"service": {}})

        node_group2.configuration = mock.Mock(
            return_value={"service": {"name": "name"}})

        cluster.node_groups = [node_group1, node_group2]

        res = pu.get_config_value_or_default(cluster=cluster,
                                             config=config)
        self.assertEqual("name", res)

        # cluster doesn't have the config, neither the node groups
        # so it returns the default value
        cluster.node_groups = []
        res = pu.get_config_value_or_default(cluster=cluster,
                                             config=config)
        self.assertEqual("default_value", res)

        # no config specified, but there's a config for the plugin
        # with this service and name
        mock_get_all_configs = mock.Mock(return_value=[config])
        mock_plugin = mock.Mock()
        mock_plugin.get_all_configs = mock_get_all_configs
        mock_get_plugin = mock.Mock(return_value=mock_plugin)
        mock_PLUGINS = mock.Mock()
        mock_PLUGINS.get_plugin = mock_get_plugin
        mock_plugins_base.PLUGINS = mock_PLUGINS

        res = pu.get_config_value_or_default(cluster=cluster,
                                             service="service", name="name")
        self.assertEqual("default_value", res)

        mock_get_plugin.assert_called_once_with("plugin_name")
        mock_get_all_configs.assert_called_once_with("hadoop_version")

        # no config especified and no existing config for this plugin
        # with this service or name
        cluster.plugin_name = "plugin_name2"
        cluster.hadoop_version = "hadoop_version2"
        self.assertRaises(RuntimeError,
                          pu.get_config_value_or_default, cluster=cluster,
                          service="newService", name="name")

        mock_get_plugin.assert_called_with("plugin_name2")
        self.assertEqual(2, mock_get_plugin.call_count)

        mock_get_all_configs.assert_called_with("hadoop_version2")
        self.assertEqual(2, mock_get_all_configs.call_count)
