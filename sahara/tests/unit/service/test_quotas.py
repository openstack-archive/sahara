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

import mock

from sahara import exceptions as exc
from sahara.service import quotas
from sahara.tests.unit import base


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
        self.override_config('use_neutron', True)
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

        type(ng).open_ports = mock.PropertyMock(return_value=[1, 2, 3])
        self.override_config('use_neutron', False)
        quotas._update_limits_for_ng(limits, ng, 3)

        self.assertEqual(6, limits['security_group_rules'])
        self.assertEqual(3, limits['ports'])
