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

import tempfile
from unittest import mock


from sahara.conductor import objects as o
from sahara import context
from sahara.tests.unit import base
import sahara.topology.topology_helper as th


class TopologyTestCase(base.SaharaTestCase):
    def setUp(self):
        super(TopologyTestCase, self).setUp()
        context.set_ctx(context.Context(None, None, None, None))

    def test_core_config(self):
        result = th.vm_awareness_core_config()
        self.assertEqual(4, len(result))
        for item in result:
            del item['description']
        className = 'org.apache.hadoop.net.NetworkTopologyWithNodeGroup'
        self.assertIn({'name': "net.topology.impl",
                       'value': className},
                      result)
        self.assertIn({'name': "net.topology.nodegroup.aware",
                       'value': 'true'},
                      result)
        className = ('org.apache.hadoop.hdfs.server.namenode.'
                     'BlockPlacementPolicyWithNodeGroup')
        self.assertIn({'name': "dfs.block.replicator.classname",
                       'value': className},
                      result)

    def test_map_red_config(self):
        result = th.vm_awareness_mapred_config()
        self.assertEqual(3, len(result))
        for item in result:
            del item['description']

        self.assertIn({'name': "mapred.jobtracker.nodegroup.aware",
                       'value': 'true'},
                      result)

        self.assertIn({'name': "mapred.task.cache.levels",
                       'value': '3'},
                      result)
        className = 'org.apache.hadoop.mapred.JobSchedulableWithNodeGroup'
        self.assertIn({'name': "mapred.jobtracker.jobSchedulable",
                       'value': className},
                      result)

    @mock.patch('sahara.utils.openstack.nova.client')
    @mock.patch('sahara.topology.topology_helper._read_compute_topology')
    @mock.patch('sahara.topology.topology_helper._read_swift_topology')
    def test_get_topology(self,
                          swift_topology,
                          compute_topology,
                          novaclient):
        nova = mock.Mock()
        novaclient.return_value = nova
        r1 = mock.Mock()
        r1.hostId = "o1"
        r2 = mock.Mock()
        r2.hostId = "o1"
        r3 = mock.Mock()
        r3.hostId = "o2"
        nova.servers.get.side_effect = [r1, r2, r3, r1, r2, r3]

        swift_topology.return_value = {"s1": "/r1"}
        compute_topology.return_value = {"o1": "/r1", "o2": "/r2"}

        i1 = o.Instance()
        i1.instance_id = "i1"
        i1.instance_name = "i1"
        i1.internal_ip = "0.0.1.1"
        i1.management_ip = "1.1.1.1"

        i2 = o.Instance()
        i2.instance_id = "i2"
        i2.instance_name = "i2"
        i2.management_ip = "1.1.1.2"
        i2.internal_ip = "0.0.1.2"

        i3 = o.Instance()
        i3.instance_id = "i3"
        i3.instance_name = "i3"
        i3.internal_ip = "1.1.1.3"
        i3.management_ip = "0.0.1.3"

        ng1 = o.NodeGroup()
        ng1.name = "1"
        ng1.instances = [i1, i2]

        ng2 = o.NodeGroup()
        ng2.name = "2"
        ng2.instances = [i3]

        cluster = o.Cluster()
        cluster.node_groups = [ng1, ng2]

        top = th.generate_topology_map(cluster, False)
        self.assertEqual({
            "i1": "/r1",
            "1.1.1.1": "/r1",
            "0.0.1.1": "/r1",
            "i2": "/r1",
            "1.1.1.2": "/r1",
            "0.0.1.2": "/r1",
            "i3": "/r2",
            "1.1.1.3": "/r2",
            "0.0.1.3": "/r2",
            "s1": "/r1"
        }, top)

        top = th.generate_topology_map(cluster, True)
        self.assertEqual({
            "i1": "/r1/o1",
            "1.1.1.1": "/r1/o1",
            "0.0.1.1": "/r1/o1",
            "i2": "/r1/o1",
            "1.1.1.2": "/r1/o1",
            "0.0.1.2": "/r1/o1",
            "i3": "/r2/o2",
            "1.1.1.3": "/r2/o2",
            "0.0.1.3": "/r2/o2",
            "s1": "/r1"
        }, top)

    def _read_swift_topology(self, content):
        temp_file = tempfile.NamedTemporaryFile()
        try:
            temp_file.write(str.encode(content))
            temp_file.flush()
            self.override_config("swift_topology_file", temp_file.name)
            return th._read_swift_topology()
        finally:
            temp_file.close()

    def test_read_swift_topology(self):
        topology = self._read_swift_topology("")
        self.assertEqual({}, topology)

        topology = self._read_swift_topology(
            "192.168.1.1 /rack1\n192.168.1.2 /rack2")
        self.assertEqual(
            {"192.168.1.1": "/rack1", "192.168.1.2": "/rack2"}, topology)

        topology = self._read_swift_topology(
            "192.168.1.1 /rack1\n192.168.1.2 /rack2\n\n")
        self.assertEqual(
            {"192.168.1.1": "/rack1", "192.168.1.2": "/rack2"}, topology)

    def _read_compute_topology(self, content):
        temp_file = tempfile.NamedTemporaryFile()
        try:
            temp_file.write(content)
            temp_file.flush()
            self.override_config("compute_topology_file", temp_file.name)
            return th._read_compute_topology()
        finally:
            temp_file.close()

    def test_read_compute_topology(self):
        topology = self._read_swift_topology("")
        self.assertEqual({}, topology)

        topology = self._read_swift_topology(
            "192.168.1.1 /rack1\n192.168.1.2 /rack2")
        self.assertEqual(2, len(topology))

        topology = self._read_swift_topology(
            "192.168.1.1 /rack1\n192.168.1.2 /rack2\n\n")
        self.assertEqual(2, len(topology))
