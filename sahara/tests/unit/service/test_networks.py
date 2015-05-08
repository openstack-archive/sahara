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

import mock

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

    @mock.patch('sahara.utils.openstack.neutron.client')
    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_neutron_with_floating(
            self, nova, upd, neutron):

        self.override_config('use_neutron', True)
        server = mock.Mock(addresses={}, id='serv_id')
        nova.return_value = server
        neutron_client = mock.Mock()
        neutron_client.list_ports.return_value = {
            'ports': [
                {'id': 'port_id'}
            ]
        }

        neutron_client.list_floatingips.return_value = {
            'floatingips': [
                {
                    'floating_ip_address': '172.1.1.1',
                    'fixed_ip_address': '10.2.2.2',
                }
            ]
        }
        neutron.return_value = neutron_client

        self.assertEqual('172.1.1.1', networks.init_instances_ips(mock.Mock()))

    @mock.patch('sahara.utils.openstack.neutron.client')
    @mock.patch('sahara.service.networks.conductor.instance_update')
    @mock.patch('sahara.utils.openstack.nova.get_instance_info')
    def test_init_instances_ips_neutron_without_floating(
            self, nova, upd, neutron):

        self.override_config('use_neutron', True)
        self.override_config('use_floating_ips', False)
        server = mock.Mock(addresses={}, id='serv_id')
        nova.return_value = server
        neutron_client = mock.Mock()
        neutron_client.list_ports.return_value = {
            'ports': [
                {'id': 'port_id'}
            ]
        }

        neutron_client.list_floatingips.return_value = {
            'floatingips': [
                {
                    'floating_ip_address': '172.1.1.1',
                    'fixed_ip_address': '10.2.2.2',
                }
            ]
        }
        neutron.return_value = neutron_client

        self.assertEqual('10.2.2.2', networks.init_instances_ips(mock.Mock()))
