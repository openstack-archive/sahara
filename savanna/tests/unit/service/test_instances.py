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

from savanna import conductor as cond
from savanna.conductor import resource as r
from savanna import context
from savanna.service import instances
from savanna.tests.unit import base as models_test_base
import savanna.utils.crypto as c


conductor = cond.API


def _resource_passthrough(*args, **kwargs):
    return True


class TestClusterRollBack(models_test_base.DbTestCase):
    def setUp(self):
        r.Resource._is_passthrough_type = _resource_passthrough
        super(TestClusterRollBack, self).setUp()

    @mock.patch('savanna.utils.openstack.nova.client')
    def test_cluster_creation_with_errors(self, novaclient):
        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node', 'task tracker'], 2)]

        cluster = _create_cluster_mock(node_groups, [])

        nova = _create_nova_mock(novaclient)
        nova.servers.create.side_effect = [_mock_instance(1),
                                           MockException("test")]

        nova.servers.list = mock.MagicMock(return_value=[_mock_instance(1)])

        with self.assertRaises(MockException):
            instances.create_cluster(cluster)

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        self.assertEqual(len(cluster_obj.node_groups[0].instances), 0)


class NodePlacementTest(models_test_base.DbTestCase):
    def setUp(self):
        r.Resource._is_passthrough_type = _resource_passthrough
        super(NodePlacementTest, self).setUp()

    @mock.patch('savanna.utils.openstack.nova.client')
    def test_one_node_groups_and_one_affinity_group(self, novaclient):
        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node'], 2)]
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

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        self.assertEqual(len(cluster_obj.node_groups[0].instances), 2)

    @mock.patch('savanna.utils.openstack.nova.client')
    def test_one_node_groups_and_no_affinity_group(self, novaclient):
        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node', 'task tracker'], 2)]

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

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        self.assertEqual(len(cluster_obj.node_groups[0].instances), 2)

    @mock.patch('savanna.utils.openstack.nova.client')
    def test_two_node_groups_and_one_affinity_group(self, novaclient):
        node_groups = [_make_ng_dict("test_group_1", "test_flavor",
                                     ["data node", "test tracker"], 2),
                       _make_ng_dict("test_group_2", "test_flavor",
                                     ["data node", "test tracker"], 1)]

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

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        inst_number = len(cluster_obj.node_groups[0].instances)
        inst_number += len(cluster_obj.node_groups[1].instances)
        self.assertEqual(inst_number, 3)


class IpManagementTest(models_test_base.DbTestCase):
    def setUp(self):
        r.Resource._is_passthrough_type = _resource_passthrough
        super(IpManagementTest, self).setUp()

    @mock.patch('savanna.utils.openstack.nova.client')
    @mock.patch('oslo.config.cfg')
    def test_ip_assignment_use_no_floating(self, cfg, novaclient):

        cfg.CONF.use_floating_ips = False
        nova = _create_nova_mock(novaclient)

        node_groups = [_make_ng_dict("test_group_1", "test_flavor",
                                     ["data node", "test tracker"], 2, 'pool'),
                       _make_ng_dict("test_group_2", "test_flavor",
                                     ["name node", "test tracker"], 1)]

        ctx = context.ctx()
        cluster = _create_cluster_mock(node_groups, ["data node"])
        instances._create_instances(cluster)

        cluster = conductor.cluster_get(ctx, cluster)
        instances_list = instances.get_instances(cluster)

        instances._assign_floating_ips(instances_list)

        nova.floating_ips.create.assert_has_calls(
            [mock.call("pool"),
             mock.call("pool")],
            any_order=False
        )

        self.assertEqual(nova.floating_ips.create.call_count, 2,
                         "Not expected floating IPs number found.")


def _make_ng_dict(name, flavor, processes, count, floating_ip_pool=None):
    ng_dict = {'name': name, 'flavor_id': flavor, 'node_processes': processes,
               'count': count}
    if floating_ip_pool:
        ng_dict.update({"floating_ip_pool": floating_ip_pool})
    return ng_dict


def _create_cluster_mock(node_groups, aa):

    user_kp = mock.Mock()
    user_kp.public_key = "123"
    private_key = c.generate_key_pair()[0]

    dct = {'name': 'test_cluster',
           'plugin_name': 'mock_plugin',
           'hadoop_version': 'mock_version',
           'default_image_id': 'initial',
           'user_keypair_id': 'user_keypair',
           'anti_affinity': aa,
           '_user_kp': user_kp,
           'private_key': private_key,
           'node_groups': node_groups}

    cluster = conductor.cluster_create(context.ctx(), dct)

    return cluster


def _mock_instance(id):
    server = mock.Mock()
    server.id = id
    server.instance_id = id
    server.status = 'ACTIVE'
    server.networks = ["n1", "n2"]
    server.addresses = {'n1': [{'OS-EXT-IPS:type': 'fixed',
                                'addr': "{0}.{0}.{0}.{0}" .format(id)}],
                        'n2': [{'OS-EXT-IPS:type': 'floating',
                                'addr': "{0}.{0}.{0}.{0}" .format(id)}]}

    server.add_floating_ip.side_effect = [True, True, True]
    return server


def _mock_ip(id):
    ip = mock.Mock()
    ip.id = id
    ip.ip = "{0}.{0}.{0}.{0}" .format(id)

    return ip


def _mock_instances(count):
    return [_mock_instance(str(i)) for i in range(1, count + 1)]


def _mock_ips(count):
    return [_mock_ip(str(i)) for i in range(1, count + 1)]


def _generate_user_data_script(cluster):
    script_template = """#!/bin/bash
echo "%(public_key)s" >> %(user_home)s/.ssh/authorized_keys
echo "%(private_key)s" > %(user_home)s/.ssh/id_rsa
"""
    return script_template % {
        "public_key": cluster.management_public_key,
        "private_key": cluster.management_private_key,
        "user_home": "/root/"
    }


def _create_nova_mock(novalcient):
    nova = mock.Mock()
    novalcient.return_value = nova
    nova.servers.create.side_effect = _mock_instances(4)
    nova.servers.get.return_value = _mock_instance(1)
    nova.floating_ips.create.side_effect = _mock_ips(4)
    images = mock.Mock()
    images.username = "root"
    nova.images.get = lambda x: images
    return nova


class MockException(Exception):
    pass
