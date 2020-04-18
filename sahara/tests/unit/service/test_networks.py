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

from sahara.service import networks
from sahara.tests.unit import base


class TestNetworks(base.SaharaTestCase):

    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_with_floating(self, nova, upd):
        server = mock.Mock()
        server.addresses = {
            'network': [
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'fixed',
                    'addr': '10.2.2.2'
                },
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'floating',
                    'addr': '172.1.1.1'
                }
            ]
        }
        nova.return_value = server

        self.assertEqual('172.1.1.1', networks.init_instances_ips(mock.Mock()))

    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_without_floating(self, nova, upd):
        self.override_config('use_floating_ips', False)
        server = mock.Mock()
        server.addresses = {
            'network': [
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'fixed',
                    'addr': '10.2.2.2'
                }
            ]
        }
        nova.return_value = server

        self.assertEqual('10.2.2.2', networks.init_instances_ips(mock.Mock()))

    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_with_proxy(self, nova, upd):

        instance = mock.Mock()
        instance.cluster.has_proxy_gateway.return_value = True
        instance.node_group.is_proxy_gateway = False
        server = mock.Mock()
        server.addresses = {
            'network': [
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'fixed',
                    'addr': '10.2.2.2'
                }
            ]
        }
        nova.return_value = server

        self.assertEqual('10.2.2.2', networks.init_instances_ips(instance))

    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_neutron_with_floating(
            self, nova, upd):

        server = mock.Mock(id='serv_id')
        server.addresses = {
            'network': [
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'floating',
                    'addr': '172.1.1.1'
                },
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'fixed',
                    'addr': '10.2.2.2'
                }
            ]
        }
        nova.return_value = server
        self.assertEqual('172.1.1.1', networks.init_instances_ips(mock.Mock()))

    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_neutron_without_floating(
            self, nova, upd):

        self.override_config('use_floating_ips', False)
        server = mock.Mock(id='serv_id')
        server.addresses = {
            'network': [
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'fixed',
                    'addr': '10.2.2.2'
                }
            ]
        }
        nova.return_value = server
        self.assertEqual('10.2.2.2', networks.init_instances_ips(mock.Mock()))

    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_with_ipv6_subnet(self, nova, upd):
        self.override_config('use_floating_ips', False)
        instance = mock.Mock()
        server = mock.Mock()
        server.addresses = {
            'network': [
                {
                    'version': 6,
                    'OS-EXT-IPS:type': 'fixed',
                    'addr': 'fe80::1234:5678:9abc:def0'
                },
                {
                    'version': 4,
                    'OS-EXT-IPS:type': 'fixed',
                    'addr': '10.2.2.2'
                }
            ]
        }
        nova.return_value = server

        self.assertEqual('10.2.2.2', networks.init_instances_ips(instance))
