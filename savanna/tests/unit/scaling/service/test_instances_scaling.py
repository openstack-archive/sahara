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
from savanna.service import instances
from savanna.tests.unit import base as models_test_base
import savanna.utils.crypto as c


def run_instance_side_effect(*args):
    return _mock_instance(args[2])


class ClusterScalingTest(models_test_base.DbTestCase):

    def test_cluster_scaling_add_new_nodes(self):
        node_groups = [m.NodeGroup("ng1", "fid1", ["namenode"], 2),
                       m.NodeGroup("ng2", "fid1", ["namenode"], 3)]
        node_groups[0]._username = 'root'
        node_groups[1]._username = 'root'
        cluster = m.Cluster("cluster1", "tenant1",
                            "vanilla", "1.2.2", "image1")
        cluster.node_groups = node_groups
        cluster.private_key = c.generate_private_key(1024)
        cluster._user_kp = mock.Mock()
        cluster._user_kp.public_key = "123"
        cluster.status = 'Active'
        with mock.patch("savanna.service.instances._run_instance") as m_m:
            m_m._run_instance.side_effect = run_instance_side_effect
            res = instances.scale_cluster(cluster, {"ng1": 4, 'ng2': 5})
            self.assertEqual(len(res), 4)
            self.assertEqual(cluster.status, "Active")

    def test_cluster_scaling_not_add_new_nodes(self):
        node_groups = [m.NodeGroup("ng1", "fid1", ["namenode"], 2)]
        node_groups[0]._username = 'root'
        cluster = m.Cluster("cluster1", "tenant1",
                            "vanilla", "1.2.2", "image1")
        cluster.node_groups = node_groups
        cluster.private_key = c.generate_private_key(1024)
        cluster._user_kp = mock.Mock()
        cluster._user_kp.public_key = "123"
        with mock.patch("savanna.service.instances._run_instance") as m_m:
            m_m._run_instance.side_effect = run_instance_side_effect
            new_instances = instances.scale_cluster(cluster, {"ng1": 2})
            self.assertEqual(len(new_instances), 0)

    def test_cluster_scaling_with_not_exists_node_group(self):
        node_groups = [m.NodeGroup("ng1", "fid1", ["namenode"], 2), ]
        node_groups[0]._username = 'root'
        cluster = m.Cluster("cluster1", "tenant1",
                            "vanilla", "1.2.2", "image1")
        cluster.node_groups = node_groups
        cluster.private_key = c.generate_private_key(1024)
        cluster._user_kp = mock.Mock()
        cluster._user_kp.public_key = "123"
        cluster.status = 'Active'
        with mock.patch("savanna.service.instances._run_instance") as m_m:
            m_m._run_instance.side_effect = run_instance_side_effect
            new_instances = instances.scale_cluster(cluster,
                                                    {"not_exists_ng": 2})
            self.assertEqual(len(new_instances), 0)
            self.assertEqual(cluster.status, 'Active')


def _mock_instance(instance_id):
    instance1 = mock.Mock()
    instance1.id = instance_id
    return instance1


def _mock_instances(count):
    return [_mock_instance(str(i)) for i in range(1, count + 1)]
