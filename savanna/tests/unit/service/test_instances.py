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

from savanna import context as ctx
import savanna.db.models as m
from savanna.service import instances
from savanna.tests.unit import base as models_test_base
import savanna.utils.crypto as c


class TestClusterRollBack(models_test_base.DbTestCase):
    @mock.patch('savanna.utils.openstack.nova.client')
    def test_cluster_creation_with_errors(self, novaclient):
        node_groups = [m.NodeGroup("test_group", "test_flavor",
                                   ["data node", "test tracker"], 2)]
        node_groups[0]._username = "root"

        cluster = _create_cluster_mock(node_groups, [])

        nova = _create_nova_mock(novaclient)
        nova.servers.create.side_effect = [_mock_instance(1),
                                           Exception("test")]

        nova.servers.list = mock.MagicMock(return_value=[_mock_instance(1)])

        with self.assertRaises(Exception):
            instances.create_cluster(cluster)

        session = ctx.ctx().session
        with session.begin():
            self.assertEqual(session.query(m.Instance).count(), 0)


class NodePlacementTest(models_test_base.DbTestCase):
    @mock.patch('savanna.utils.openstack.nova.client')
    def test_one_node_groups_and_one_affinity_group(self, novaclient):
        node_groups = [m.NodeGroup("test_group", "test_flavor",
                                   ["data node", "test tracker"], 2)]
        node_groups[0]._username = "root"
        cluster = _create_cluster_mock(node_groups, ["data node"])
        nova = _create_nova_mock(novaclient)
        instances._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)

        nova.servers.create.assert_has_calls(
            [mock.call("test_cluster-test_group-001",
                       "initial",
                       "test_flavor",
                       scheduler_hints=None,
                       userdata=userdata,
                       key_name='user_keypair'),
             mock.call("test_cluster-test_group-002",
                       "initial",
                       "test_flavor",
                       scheduler_hints={'different_host': ["1"]},
                       userdata=userdata,
                       key_name='user_keypair')],
            any_order=False)

        session = ctx.ctx().session
        with session.begin():
            self.assertEqual(session.query(m.Instance).count(), 2)

    @mock.patch('savanna.utils.openstack.nova.client')
    def test_one_node_groups_and_no_affinity_group(self, novaclient):
        node_groups = [m.NodeGroup("test_group", "test_flavor",
                                   ["data node", "test tracker"], 2)]
        node_groups[0]._username = "root"
        cluster = _create_cluster_mock(node_groups, [])
        nova = _create_nova_mock(novaclient)
        instances._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)

        nova.servers.create.assert_has_calls(
            [mock.call("test_cluster-test_group-001",
                       "initial",
                       "test_flavor",
                       scheduler_hints=None,
                       userdata=userdata,
                       key_name='user_keypair'),
             mock.call("test_cluster-test_group-002",
                       "initial",
                       "test_flavor",
                       scheduler_hints=None,
                       userdata=userdata,
                       key_name='user_keypair')],
            any_order=False)

        session = ctx.ctx().session
        with session.begin():
            self.assertEqual(session.query(m.Instance).count(), 2)

    @mock.patch('savanna.utils.openstack.nova.client')
    def test_two_node_groups_and_one_affinity_group(self, novaclient):
        node_groups = [m.NodeGroup("test_group_1", "test_flavor",
                                   ["data node", "test tracker"], 2),
                       m.NodeGroup("test_group_2", "test_flavor",
                                   ["data node", "test tracker"], 1)]
        node_groups[0]._username = "root"
        node_groups[1]._username = "root"
        cluster = _create_cluster_mock(node_groups, ["data node"])
        nova = _create_nova_mock(novaclient)
        instances._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)

        nova.servers.create.assert_has_calls(
            [mock.call("test_cluster-test_group_1-001",
                       "initial",
                       "test_flavor",
                       scheduler_hints=None,
                       userdata=userdata,
                       key_name='user_keypair'),
             mock.call("test_cluster-test_group_1-002",
                       "initial",
                       "test_flavor",
                       scheduler_hints={'different_host': ["1"]},
                       userdata=userdata,
                       key_name='user_keypair'),
             mock.call("test_cluster-test_group_2-001",
                       "initial",
                       "test_flavor",
                       scheduler_hints={'different_host': ["1", "2"]},
                       userdata=userdata,
                       key_name='user_keypair')],
            any_order=False)

        session = ctx.ctx().session
        with session.begin():
            self.assertEqual(session.query(m.Instance).count(), 3)


def _create_cluster_mock(node_groups, aa):
    cluster = m.Cluster("test_cluster", "tenant_id", "mock_plugin",
                        "mock_version", "initial",
                        user_keypair_id='user_keypair', anti_affinity=aa)

    cluster._user_kp = mock.Mock()
    cluster._user_kp.public_key = "123"
    cluster.private_key = c.generate_private_key()
    cluster.node_groups = node_groups

    return cluster


def _mock_instance(id):
    instance1 = mock.Mock()
    instance1.id = id
    return instance1


def _mock_instances(count):
    return [_mock_instance(str(i)) for i in range(1, count + 1)]


def _generate_user_data_script(cluster):
    script_template = """#!/bin/bash
echo "%(public_key)s" >> %(user_home)s/.ssh/authorized_keys
echo "%(private_key)s" > %(user_home)s/.ssh/id_rsa
"""
    key = c.private_key_to_public_key(cluster.private_key)
    return script_template % {
        "public_key": key,
        "private_key": cluster.private_key,
        "user_home": "/root/"
    }


def _create_nova_mock(novalcient):
    nova = mock.Mock()
    novalcient.return_value = nova
    nova.servers.create.side_effect = _mock_instances(3)
    return nova
