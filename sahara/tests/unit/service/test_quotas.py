# Copyright (c) 2015 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from unittest import mock

from oslo_utils import uuidutils
import testtools

from sahara import exceptions as exc
from sahara.service import quotas
from sahara.tests.unit import base


class FakeFlavor(object):
    def __init__(self, ram, vcpu):
        self.ram = ram
        self.vcpus = vcpu


class FakeNovaClient(object):
    def __init__(self, lims):
        self.lims = lims

    @property
    def limits(self):
        return self

    def to_dict(self):
        return self.lims

    def get(self):
        return self

    @property
    def flavors(self):
        return {'id1': FakeFlavor(4, 2)}


class CinderLimit(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value


class FakeCinderClient(object):
    def __init__(self, lims):
        self.lims = lims

    @property
    def limits(self):
        return self

    @property
    def absolute(self):
        return self.lims

    def get(self):
        return self

    def to_dict(self):
        return self


class FakeNeutronClient(object):
    def __init__(self, lims):
        self.lims = lims

    def show_quota(self, tenant_id):
        return {'quota': self.lims}

    def list_floatingips(self, tenant_id):
        return {'floatingips': [1, 2, 3, 4, 5]}

    def list_security_groups(self, tenant_id):
        return {'security_groups': [1, 2, 3, 4, 5, 6, 7]}

    def list_security_group_rules(self, tenant_id):
        return {'security_groups_rules': [1, 2, 3]}

    def list_ports(self, tenant_id):
        return {'ports': []}


class FakeCluster(object):
    def __init__(self, node_groups):
        self.node_groups = node_groups


class FakeNodeGroup(object):
    def __init__(self, count, auto_sg, volumes_size, volumes_per_node, pool,
                 flavor_id, ports):
        self.count = count
        self.auto_security_group = auto_sg
        self.volumes_size = volumes_size
        self.volumes_per_node = volumes_per_node
        self.floating_ip_pool = pool
        self.flavor_id = flavor_id
        self.open_ports = ports
        self.id = uuidutils.generate_uuid()


nova_limits = {
    'absolute': {
        'maxTotalRAMSize': 10,
        'totalRAMUsed': 1,
        'maxTotalCores': 15,
        'totalCoresUsed': 5,
        'maxTotalInstances': 5,
        'totalInstancesUsed': 2,
        'maxTotalFloatingIps': 300,
        'totalFloatingIpsUsed': 100,
        'maxSecurityGroups': 50,
        'totalSecurityGroupsUsed': 22,
        'maxSecurityGroupRules': -1,  # unlimited quota test
    }
}

neutron_limits = {
    'floatingip': 2345,
    'security_group': 1523,
    'security_group_rule': 332,
    'port': -1
}

cinder_limits = [
    CinderLimit(name='maxTotalVolumes', value=5),
    CinderLimit(name='totalVolumesUsed', value=3),
    CinderLimit(name='maxTotalVolumeGigabytes', value=10),
    CinderLimit(name='totalGigabytesUsed', value=2)
]


class TestQuotas(base.SaharaTestCase):
    LIST_LIMITS = ['ram', 'cpu', 'instances', 'floatingips',
                   'security_groups', 'security_group_rules', 'ports',
                   'volumes', 'volume_gbs']

    def test_get_zero_limits(self):
        res = quotas._get_zero_limits()
        self.assertEqual(9, len(res))
        for key in self.LIST_LIMITS:
            self.assertEqual(0, res[key])

    @mock.patch('sahara.service.quotas._get_avail_limits')
    def test_check_limits(self, mock_avail_limits):
        avail_limits = {}
        req_limits = {}

        for key in self.LIST_LIMITS:
            avail_limits[key] = quotas.UNLIMITED
            req_limits[key] = 100500
        mock_avail_limits.return_value = avail_limits
        self.assertIsNone(quotas._check_limits(req_limits))

        for key in self.LIST_LIMITS:
            avail_limits[key] = 2
            req_limits[key] = 1
        mock_avail_limits.return_value = avail_limits
        self.assertIsNone(quotas._check_limits(req_limits))

        for key in self.LIST_LIMITS:
            req_limits[key] = 2
        self.assertIsNone(quotas._check_limits(req_limits))

        for key in self.LIST_LIMITS:
            req_limits[key] = 3
        self.assertRaises(exc.QuotaException, quotas._check_limits, req_limits)

    @mock.patch('sahara.utils.openstack.nova.client')
    def test_update_limits_for_ng(self, nova_mock):
        flavor_mock = mock.Mock()
        type(flavor_mock).ram = mock.PropertyMock(return_value=4)
        type(flavor_mock).vcpus = mock.PropertyMock(return_value=2)

        flavor_get_mock = mock.Mock()
        flavor_get_mock.get.return_value = flavor_mock

        type(nova_mock.return_value).flavors = mock.PropertyMock(
            return_value=flavor_get_mock)

        ng = mock.Mock()
        type(ng).flavor_id = mock.PropertyMock(return_value=3)
        type(ng).floating_ip_pool = mock.PropertyMock(return_value='pool')
        type(ng).volumes_per_node = mock.PropertyMock(return_value=4)
        type(ng).volumes_size = mock.PropertyMock(return_value=5)
        type(ng).auto_security_group = mock.PropertyMock(return_value=True)
        type(ng).open_ports = mock.PropertyMock(return_value=[1111, 2222])

        limits = quotas._get_zero_limits()
        quotas._update_limits_for_ng(limits, ng, 3)

        self.assertEqual(3, limits['instances'])
        self.assertEqual(12, limits['ram'])
        self.assertEqual(6, limits['cpu'])
        self.assertEqual(3, limits['floatingips'])
        self.assertEqual(12, limits['volumes'])
        self.assertEqual(60, limits['volume_gbs'])
        self.assertEqual(1, limits['security_groups'])
        self.assertEqual(5, limits['security_group_rules'])
        self.assertEqual(3, limits['ports'])

    @mock.patch('sahara.utils.openstack.nova.client',
                return_value=FakeNovaClient(nova_limits))
    def test_get_nova_limits(self, nova):
        self.assertEqual(
            {'cpu': 10, 'instances': 3, 'ram': 9}, quotas._get_nova_limits())

    @mock.patch('sahara.utils.openstack.cinder.client',
                return_value=FakeCinderClient(cinder_limits))
    def test_get_cinder_limits(self, cinder):
        self.assertEqual({'volumes': 2, 'volume_gbs': 8},
                         quotas._get_cinder_limits())

    @mock.patch('sahara.utils.openstack.neutron.client',
                return_value=FakeNeutronClient(neutron_limits))
    def test_neutron_limits(self, neutron):
        self.assertEqual({'floatingips': 2340,
                          'ports': 'unlimited',
                          'security_group_rules': 332,
                          'security_groups': 1516},
                         quotas._get_neutron_limits())

    @mock.patch("sahara.utils.openstack.cinder.check_cinder_exists",
                return_value=True)
    @mock.patch('sahara.utils.openstack.nova.client',
                return_value=FakeNovaClient(nova_limits))
    @mock.patch('sahara.utils.openstack.cinder.client',
                return_value=FakeCinderClient(cinder_limits))
    @mock.patch('sahara.utils.openstack.neutron.client',
                return_value=FakeNeutronClient(neutron_limits))
    def test_limits_for_cluster(self, p1, p2, p3, p4):
        ng = [FakeNodeGroup(1, False, 0, 0, None, 'id1', [1, 2, 3])]
        quotas.check_cluster(FakeCluster(ng))

        with testtools.ExpectedException(exc.QuotaException):
            quotas.check_cluster(FakeCluster([FakeNodeGroup(
                1, False, 3, 3, None, 'id1', [1, 2, 3])]))

        ng = [FakeNodeGroup(1, False, 0, 0, None, 'id1', [1, 2, 3]),
              FakeNodeGroup(0, False, 0, 0, None, 'id1', [1, 2, 3])]
        quotas.check_scaling(FakeCluster(ng), {}, {ng[1].id: 1})

        with testtools.ExpectedException(exc.QuotaException):
            quotas.check_scaling(FakeCluster(ng), {}, {ng[1].id: 3})
