# Copyright (c) 2015 TellesNobrega
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

from sahara import conductor as cond
from sahara import context
from sahara.plugins import base as pb
from sahara.plugins import exceptions as ex
from sahara.plugins.storm import plugin as pl
from sahara.service.edp.storm import engine
from sahara.tests.unit import base
from sahara.utils import edp


conductor = cond.API


class StormPluginTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(StormPluginTest, self).setUp()
        self.override_config("plugins", ["storm"])
        self.master_host = "master"
        self.master_inst = "6789"
        self.storm_topology_name = 'topology1'
        pb.setup_plugins()

    def _make_master_instance(self, return_code=0):
        master = mock.Mock()
        master.execute_command.return_value = (return_code,
                                               self.storm_topology_name)
        master.hostname.return_value = self.master_host
        master.id = self.master_inst
        return master

    def _get_cluster(self, name, version):
        cluster_dict = {
            'name': name,
            'plugin_name': 'storm',
            'hadoop_version': version,
            'node_groups': []}
        return cluster_dict

    def test_validate_existing_ng_scaling(self):
        data = [
            {'name': 'master',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['nimbus']},
            {'name': 'slave',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['supervisor']},
            {'name': 'zookeeper',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['zookeeper']}
        ]

        cluster_data_101 = self._get_cluster('cluster_1.0.1', '1.0.1')
        cluster_data_110 = self._get_cluster('cluster_1.1.0', '1.1.0')
        cluster_data_120 = self._get_cluster('cluster_1.2.0', '1.2')
        cluster_data_101['node_groups'] = data
        cluster_data_110['node_groups'] = data
        cluster_data_120['node_groups'] = data

        clusters = [cluster_data_101, cluster_data_110, cluster_data_120]

        for cluster_data in clusters:
            cluster = conductor.cluster_create(context.ctx(), cluster_data)
            plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
            supervisor_id = [node.id for node in cluster.node_groups
                             if node.name == 'supervisor']
            self.assertIsNone(
                plugin._validate_existing_ng_scaling(cluster,
                                                     supervisor_id))

    @mock.patch("sahara.plugins.storm.plugin.utils")
    def test_validate(self, mock_utils):

        cluster_data = self._get_cluster('cluster', '1.1.0')
        cluster = conductor.cluster_create(context.ctx(), cluster_data)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)

        # number of nimbus nodes != 1 should raise an exception
        fake_ng = mock.Mock()
        fake_ng.count = 0
        mock_ng = mock.Mock(return_value=[fake_ng])
        mock_utils.get_node_groups = mock_ng

        self.assertRaises(ex.RequiredServiceMissingException,
                          plugin.validate, cluster)

        mock_ng.assert_called_once_with(cluster, "nimbus")

        fake_ng.count = 2
        self.assertRaises(ex.InvalidComponentCountException, plugin.validate,
                          cluster)

        mock_ng.assert_called_with(cluster, "nimbus")
        self.assertEqual(2, mock_ng.call_count)

        # no supervisor should raise an exception
        fake_nimbus = mock.Mock()
        fake_nimbus.count = 1

        fake_supervisor = mock.Mock()
        fake_supervisor.count = 0

        mock_ng = mock.Mock(side_effect=[[fake_nimbus], [fake_supervisor]])
        mock_utils.get_node_groups = mock_ng

        self.assertRaises(ex.InvalidComponentCountException, plugin.validate,
                          cluster)

        mock_ng.assert_any_call(cluster, "nimbus")
        mock_ng.assert_any_call(cluster, "supervisor")
        self.assertEqual(2, mock_ng.call_count)

        # one nimbus and one or more supervisors should not raise an exception
        fake_nimbus.count = 1
        fake_supervisor.count = 2

        mock_ng = mock.Mock(side_effect=[[fake_nimbus], [fake_supervisor]])
        mock_utils.get_node_groups = mock_ng

        plugin.validate(cluster)

        mock_ng.assert_any_call(cluster, "nimbus")
        mock_ng.assert_any_call(cluster, "supervisor")
        self.assertEqual(2, mock_ng.call_count)

    def test_validate_additional_ng_scaling(self):
        data = [
            {'name': 'master',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['nimbus']},
            {'name': 'slave',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['supervisor']},
            {'name': 'zookeeper',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['zookeeper']},
            {'name': 'slave2',
             'flavor_id': '42',
             'count': 0,
             'node_processes': ['supervisor']}
        ]

        cluster_data_101 = self._get_cluster('cluster_1.0.1', '1.0.1')
        cluster_data_110 = self._get_cluster('cluster_1.1.0', '1.1.0')
        cluster_data_120 = self._get_cluster('cluster_1.2.0', '1.2')
        cluster_data_101['node_groups'] = data
        cluster_data_110['node_groups'] = data
        cluster_data_120['node_groups'] = data

        clusters = [cluster_data_101, cluster_data_110, cluster_data_120]

        for cluster_data in clusters:
            cluster = conductor.cluster_create(context.ctx(), cluster_data)
            plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
            supervisor_id = [node.id for node in cluster.node_groups
                             if node.name == 'supervisor']
            self.assertIsNone(
                plugin._validate_additional_ng_scaling(cluster,
                                                       supervisor_id))

    def test_validate_existing_ng_scaling_raises(self):
        data = [
            {'name': 'master',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['nimbus']},
            {'name': 'slave',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['supervisor']},
            {'name': 'zookeeper',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['zookeeper']}
        ]

        cluster_data_101 = self._get_cluster('cluster_1.0.1', '1.0.1')
        cluster_data_110 = self._get_cluster('cluster_1.1.0', '1.1.0')
        cluster_data_120 = self._get_cluster('cluster_1.2.0', '1.2')
        cluster_data_101['node_groups'] = data
        cluster_data_110['node_groups'] = data
        cluster_data_120['node_groups'] = data

        clusters = [cluster_data_101, cluster_data_110, cluster_data_120]

        for cluster_data in clusters:
            cluster = conductor.cluster_create(context.ctx(), cluster_data)
            plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
            master_id = [node.id for node in cluster.node_groups
                         if node.name == 'master']
            self.assertRaises(ex.NodeGroupCannotBeScaled,
                              plugin._validate_existing_ng_scaling,
                              cluster, master_id)

    def test_validate_additional_ng_scaling_raises(self):
        data = [
            {'name': 'master',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['nimbus']},
            {'name': 'slave',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['supervisor']},
            {'name': 'zookeeper',
             'flavor_id': '42',
             'count': 1,
             'node_processes': ['zookeeper']},
            {'name': 'master2',
             'flavor_id': '42',
             'count': 0,
             'node_processes': ['nimbus']}
        ]

        cluster_data_101 = self._get_cluster('cluster_1.0.1', '1.0.1')
        cluster_data_110 = self._get_cluster('cluster_1.1.0', '1.1.0')
        cluster_data_120 = self._get_cluster('cluster_1.2.0', '1.2')
        cluster_data_101['node_groups'] = data
        cluster_data_110['node_groups'] = data
        cluster_data_120['node_groups'] = data

        clusters = [cluster_data_101, cluster_data_110, cluster_data_120]

        for cluster_data in clusters:
            cluster = conductor.cluster_create(context.ctx(), cluster_data)
            plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
            master_id = [node.id for node in cluster.node_groups
                         if node.name == 'master2']
            self.assertRaises(ex.NodeGroupCannotBeScaled,
                              plugin._validate_existing_ng_scaling,
                              cluster, master_id)

    def test_get_open_port(self):
        plugin_storm = pl.StormProvider()
        cluster = mock.Mock()
        ng = mock.Mock()
        ng.node_processes = ['nimbus']
        cluster.node_groups = [ng]
        ng.cluster = cluster
        ports = plugin_storm.get_open_ports(ng)
        self.assertEqual([8080], ports)

    def _test_engine(self, version, job_type, eng):
        cluster_dict = self._get_cluster('demo', version)

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        self.assertIsInstance(plugin.get_edp_engine(cluster, job_type), eng)

    def test_plugin101_edp_storm_engine(self):
        self._test_engine('1.0.1', edp.JOB_TYPE_STORM,
                          engine.StormJobEngine)

    def test_plugin101_edp_storm_pyleus_engine(self):
        self._test_engine('1.0.1', edp.JOB_TYPE_PYLEUS,
                          engine.StormJobEngine)

    def test_plugin110_edp_storm_engine(self):
        self._test_engine('1.1.0', edp.JOB_TYPE_STORM,
                          engine.StormJobEngine)

    def test_plugin110_edp_storm_pyleus_engine(self):
        self._test_engine('1.1.0', edp.JOB_TYPE_PYLEUS,
                          engine.StormJobEngine)

    def test_plugin120_edp_storm_engine(self):
        self._test_engine('1.2', edp.JOB_TYPE_STORM,
                          engine.StormJobEngine)

    def test_plugin120_edp_storm_pyleus_engine(self):
        self._test_engine('1.2', edp.JOB_TYPE_PYLEUS,
                          engine.StormJobEngine)
