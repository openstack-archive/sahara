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

from novaclient import exceptions as nova_exceptions
import six

from sahara import conductor as cond
from sahara import context
from sahara.service import direct_engine as e
from sahara.tests.unit import base
import sahara.utils.crypto as c
from sahara.utils import general as g


conductor = cond.API


class AbstractInstanceTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(AbstractInstanceTest, self).setUp()

        self.engine = e.DirectEngine()

        self.is_passthrough_patcher = mock.patch(
            'sahara.conductor.resource.Resource._is_passthrough_type')
        self.is_passthrough_patcher.start().return_value = True

        self.novaclient_patcher = mock.patch(
            'sahara.utils.openstack.nova.client')
        self.nova = _create_nova_mock(self.novaclient_patcher.start())

        self.get_userdata_patcher = mock.patch(
            'sahara.utils.remote.get_userdata_template')
        self.get_userdata_patcher.start().return_value = ''

    def tearDown(self):
        self.get_userdata_patcher.stop()
        self.novaclient_patcher.stop()
        self.is_passthrough_patcher.stop()

        super(AbstractInstanceTest, self).tearDown()


class TestClusterRollBack(AbstractInstanceTest):

    def test_cluster_creation_with_errors(self):
        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node', 'task tracker'], 2)]

        cluster = _create_cluster_mock(node_groups, [])

        self.nova.servers.create.side_effect = [_mock_instance(1),
                                                MockException("test")]

        self.nova.servers.list.return_value = [_mock_instance(1)]

        with self.assertRaises(MockException):
            self.engine.create_cluster(cluster)

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        self.assertEqual(len(cluster_obj.node_groups[0].instances), 0)


class NodePlacementTest(AbstractInstanceTest):

    def test_one_node_groups_and_one_affinity_group(self):
        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node'], 2)]
        cluster = _create_cluster_mock(node_groups, ["data node"])
        self.engine._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)

        self.nova.servers.create.assert_has_calls(
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

    def test_one_node_groups_and_no_affinity_group(self):
        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node', 'task tracker'], 2)]

        cluster = _create_cluster_mock(node_groups, [])
        self.engine._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)

        self.nova.servers.create.assert_has_calls(
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

    def test_two_node_groups_and_one_affinity_group(self):
        node_groups = [_make_ng_dict("test_group_1", "test_flavor",
                                     ["data node", "test tracker"], 2),
                       _make_ng_dict("test_group_2", "test_flavor",
                                     ["data node", "test tracker"], 1)]

        cluster = _create_cluster_mock(node_groups, ["data node"])
        self.engine._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)

        def _find_created_at(idx):
            """Find the #N instance creation call.

            To determine which instance was created first, we should check
            scheduler hints For example we should find call with scheduler
            hint different_hosts = [1, 2] and it's the third call of instance
            create.
            """
            different_hosts = []
            for instance_id in six.moves.xrange(1, idx):
                different_hosts.append(str(instance_id))
            scheduler_hints = ({'different_host': different_hosts}
                               if different_hosts else None)

            for call in self.nova.servers.create.mock_calls:
                if call[2]['scheduler_hints'] == scheduler_hints:
                    return call[1][0]

            self.fail("Couldn't find call with scheduler_hints='%s'"
                      % scheduler_hints)

        # find instance names in instance create calls
        instance_names = []
        for idx in six.moves.xrange(1, 4):
            instance_name = _find_created_at(idx)
            if instance_name in instance_names:
                self.fail("Create instance was called twice with the same "
                          "instance name='%s'" % instance_name)
            instance_names.append(instance_name)

        self.assertEqual(3, len(instance_names))
        self.assertItemsEqual([
            'test_cluster-test_group_1-001',
            'test_cluster-test_group_1-002',
            'test_cluster-test_group_2-001',
        ], instance_names)

        self.nova.servers.create.assert_has_calls(
            [mock.call(instance_names[0],
                       "initial",
                       "test_flavor",
                       scheduler_hints=None,
                       userdata=userdata,
                       key_name='user_keypair'),
             mock.call(instance_names[1],
                       "initial",
                       "test_flavor",
                       scheduler_hints={'different_host': ["1"]},
                       userdata=userdata,
                       key_name='user_keypair'),
             mock.call(instance_names[2],
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


class IpManagementTest(AbstractInstanceTest):
    def setUp(self):
        super(IpManagementTest, self).setUp()
        self.engine = e.DirectEngine()

    def test_ip_assignment_use_no_floating(self):
        self.override_config("use_floating_ips", False)

        node_groups = [_make_ng_dict("test_group_1", "test_flavor",
                                     ["data node", "test tracker"], 2,
                                     'pool'),
                       _make_ng_dict("test_group_2", "test_flavor",
                                     ["name node", "test tracker"], 1)]

        ctx = context.ctx()
        cluster = _create_cluster_mock(node_groups, ["data node"])
        self.engine._create_instances(cluster)

        cluster = conductor.cluster_get(ctx, cluster)
        instances_list = g.get_instances(cluster)

        self.engine._assign_floating_ips(instances_list)

        self.nova.floating_ips.create.assert_has_calls(
            [mock.call("pool"), mock.call("pool")])

        self.assertEqual(self.nova.floating_ips.create.call_count, 2,
                         "Not expected floating IPs number found.")


class ShutdownClusterTest(AbstractInstanceTest):
    def test_delete_floating_ips(self):
        node_groups = [_make_ng_dict("test_group_1", "test_flavor",
                                     ["data node", "test tracker"], 2, 'pool')]

        ctx = context.ctx()
        cluster = _create_cluster_mock(node_groups, ["datanode"])
        self.engine._create_instances(cluster)

        cluster = conductor.cluster_get(ctx, cluster)
        instances_list = g.get_instances(cluster)

        self.engine._assign_floating_ips(instances_list)

        self.engine._shutdown_instances(cluster)
        self.assertEqual(self.nova.floating_ips.delete.call_count, 2,
                         "Not expected floating IPs number found in delete")
        self.assertEqual(self.nova.servers.delete.call_count, 2,
                         "Not expected")


def _make_ng_dict(name, flavor, processes, count, floating_ip_pool=None):
    ng_dict = {'name': name, 'flavor_id': flavor, 'node_processes': processes,
               'count': count, 'image_username': 'root'}
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
echo "%(public_key)s" >> %(user_home)s/.ssh/authorized_keys\n
"""
    return script_template % {
        "public_key": cluster.management_public_key,
        "user_home": "/root/"
    }


def _create_nova_mock(novaclient):
    nova = mock.Mock()
    novaclient.return_value = nova
    nova.servers.create.side_effect = _mock_instances(4)
    nova.servers.get.return_value = _mock_instance(1)
    nova.floating_ips.create.side_effect = _mock_ips(4)
    nova.floating_ips.findall.return_value = _mock_ips(1)
    nova.floating_ips.delete.side_effect = _mock_deletes(2)
    images = mock.Mock()
    images.username = "root"
    nova.images.get = lambda x: images
    return nova


def _mock_deletes(count):
    return [_mock_delete(i) for i in range(1, count + 1)]


def _mock_delete(id):
    if id == 1:
        return None
    return nova_exceptions.NotFound(code=404)


class MockException(Exception):
    pass
