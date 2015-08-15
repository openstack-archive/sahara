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

from sahara import conductor as cond
from sahara import context
from sahara.service import direct_engine as e
from sahara.service import ops
from sahara.tests.unit import base
from sahara.utils import cluster as cluster_utils
from sahara.utils import crypto as c


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
        self.nova.server_groups.findall.return_value = []
        self.nova.floating_ips.findall.__name__ = 'findall'
        self.nova.floating_ips.delete.__name__ = 'delete'

        self.get_userdata_patcher = mock.patch(
            'sahara.utils.remote.get_userdata_template')
        self.get_userdata_patcher.start().return_value = ''

    def tearDown(self):
        self.get_userdata_patcher.stop()
        self.novaclient_patcher.stop()
        self.is_passthrough_patcher.stop()

        super(AbstractInstanceTest, self).tearDown()


class TestClusterRollBack(AbstractInstanceTest):

    @mock.patch('sahara.service.direct_engine.DirectEngine._check_if_deleted')
    @mock.patch('sahara.service.ops._prepare_provisioning')
    @mock.patch('sahara.service.ops.INFRA')
    def test_cluster_creation_with_errors(self, infra, prepare,
                                          deleted_checker):
        infra.create_cluster.side_effect = self.engine.create_cluster
        infra.rollback_cluster.side_effect = self.engine.rollback_cluster

        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node', 'task tracker'], 2)]

        cluster = _create_cluster_mock(node_groups, [])

        prepare.return_value = (context.ctx(), cluster, mock.Mock())

        self.nova.servers.create.side_effect = [_mock_instance(1),
                                                MockException("test")]

        self.nova.servers.list.return_value = [_mock_instance(1)]

        deleted_checker.return_value = True

        ops._provision_cluster(cluster.id)

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        self.assertEqual(0, len(cluster_obj.node_groups[0].instances))


class NodePlacementTest(AbstractInstanceTest):

    def test_one_node_groups_and_one_affinity_group(self):
        self.nova.server_groups.create.return_value = mock.Mock(id='123')

        node_groups = [_make_ng_dict('test_group', 'test_flavor',
                                     ['data node'], 2)]
        cluster = _create_cluster_mock(node_groups, ["data node"])
        self.engine._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)
        self.nova.servers.create.assert_has_calls(
            [mock.call("test_cluster-test_group-001",
                       "initial",
                       "test_flavor",
                       scheduler_hints={'group': "123"},
                       userdata=userdata,
                       key_name='user_keypair',
                       security_groups=None,
                       availability_zone=None),
             mock.call("test_cluster-test_group-002",
                       "initial",
                       "test_flavor",
                       scheduler_hints={'group': "123"},
                       userdata=userdata,
                       key_name='user_keypair',
                       security_groups=None,
                       availability_zone=None)],
            any_order=False)

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        self.assertEqual(2, len(cluster_obj.node_groups[0].instances))

    def test_one_node_groups_and_no_affinity_group(self):
        self.nova.server_groups.create.return_value = mock.Mock(id='123')

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
                       key_name='user_keypair',
                       security_groups=None,
                       availability_zone=None),
             mock.call("test_cluster-test_group-002",
                       "initial",
                       "test_flavor",
                       scheduler_hints=None,
                       userdata=userdata,
                       key_name='user_keypair',
                       security_groups=None,
                       availability_zone=None)],
            any_order=False)

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        self.assertEqual(2, len(cluster_obj.node_groups[0].instances))

    def test_two_node_groups_and_one_affinity_group(self):
        self.nova.server_groups.create.return_value = mock.Mock(id='123')

        node_groups = [_make_ng_dict("test_group_1", "test_flavor",
                                     ["data node", "test tracker"], 2),
                       _make_ng_dict("test_group_2", "test_flavor",
                                     ["data node", "test tracker"], 1)]

        cluster = _create_cluster_mock(node_groups, ["data node"])
        self.engine._create_instances(cluster)
        userdata = _generate_user_data_script(cluster)

        self.nova.servers.create.assert_has_calls(
            [mock.call('test_cluster-test_group_1-001',
                       "initial",
                       "test_flavor",
                       scheduler_hints={'group': "123"},
                       userdata=userdata,
                       key_name='user_keypair',
                       security_groups=None,
                       availability_zone=None),
             mock.call('test_cluster-test_group_1-002',
                       "initial",
                       "test_flavor",
                       scheduler_hints={'group': "123"},
                       userdata=userdata,
                       key_name='user_keypair',
                       security_groups=None,
                       availability_zone=None),
             mock.call('test_cluster-test_group_2-001',
                       "initial",
                       "test_flavor",
                       scheduler_hints={'group': "123"},
                       userdata=userdata,
                       key_name='user_keypair',
                       security_groups=None,
                       availability_zone=None)],
            any_order=False)

        ctx = context.ctx()
        cluster_obj = conductor.cluster_get_all(ctx)[0]
        inst_number = len(cluster_obj.node_groups[0].instances)
        inst_number += len(cluster_obj.node_groups[1].instances)
        self.assertEqual(3, inst_number)


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
        instances_list = cluster_utils.get_instances(cluster)

        self.engine._assign_floating_ips(instances_list)

        self.nova.floating_ips.create.assert_has_calls(
            [mock.call("pool"), mock.call("pool")])

        self.assertEqual(2, self.nova.floating_ips.create.call_count,
                         "Not expected floating IPs number found.")


class ShutdownClusterTest(AbstractInstanceTest):

    @mock.patch('sahara.service.direct_engine.DirectEngine._check_if_deleted')
    @mock.patch('sahara.service.direct_engine.DirectEngine.'
                '_map_security_groups')
    def test_delete_floating_ips(self, map_mock, deleted_checker):
        node_groups = [_make_ng_dict("test_group_1", "test_flavor",
                                     ["data node", "test tracker"], 2, 'pool')]
        map_mock.return_value = []
        ctx = context.ctx()
        cluster = _create_cluster_mock(node_groups, ["datanode"])
        self.engine._create_instances(cluster)

        cluster = conductor.cluster_get(ctx, cluster)
        instances_list = cluster_utils.get_instances(cluster)

        self.engine._assign_floating_ips(instances_list)

        deleted_checker.return_value = True

        self.engine._shutdown_instances(cluster)
        self.assertEqual(2, self.nova.floating_ips.delete.call_count,
                         "Not expected floating IPs number found in delete")
        self.assertEqual(2, self.nova.servers.delete.call_count,
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
# ====== COMMENT OUT Defaults requiretty in /etc/sudoers ========
sed '/^Defaults    requiretty*/ s/^/#/' -i /etc/sudoers\n
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
