# Copyright (c) 2013 Hortonworks, Inc.
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

from sahara.tests.unit import base
from sahara.utils.openstack import neutron as neutron_client


class NeutronClientTest(base.SaharaTestCase):
    @mock.patch("sahara.utils.openstack.keystone.token_auth")
    @mock.patch("neutronclient.neutron.client.Client")
    def test_get_router(self, patched, token_auth):
        patched.side_effect = _test_get_neutron_client
        neutron = neutron_client.NeutronClient(
            '33b47310-b7a8-4559-bf95-45ba669a448e', None, None)
        self.assertEqual('6c4d4e32-3667-4cd4-84ea-4cc1e98d18be',
                         neutron.get_router())


def _test_get_neutron_client(api_version, *args, **kwargs):
    return FakeNeutronClient()


class FakeNeutronClient(object):
    def list_routers(self):
        return {"routers": [{"status": "ACTIVE", "external_gateway_info": {
            "network_id": "61f95d3f-495e-4409-8c29-0b806283c81e"},
            "name": "router1", "admin_state_up": True,
            "tenant_id": "903809ded3434f8d89948ee71ca9f5bb",
            "routes": [],
            "id": "6c4d4e32-3667-4cd4-84ea-4cc1e98d18be"}]}

    def list_ports(self, device_id=None):
        return {"ports": [
            {"status": "ACTIVE", "name": "", "admin_state_up": True,
             "network_id": "33b47310-b7a8-4559-bf95-45ba669a448e",
             "tenant_id": "903809ded3434f8d89948ee71ca9f5bb",
             "binding:vif_type": "ovs", "device_owner": "compute:None",
             "binding:capabilities": {"port_filter": True},
             "mac_address": "fa:16:3e:69:25:1c", "fixed_ips": [
                {"subnet_id": "bfa9d0a1-9efb-4bff-bd2b-c103c053560f",
                 "ip_address": "10.0.0.8"}],
             "id": "0f3df685-bc55-4314-9b76-835e1767b78f",
             "security_groups": ["f9fee2a2-bb0b-44e4-8092-93a43dc45cda"],
             "device_id": "c2129c18-6707-4f07-94cf-00b2fef8eea7"},
            {"status": "ACTIVE", "name": "", "admin_state_up": True,
             "network_id": "33b47310-b7a8-4559-bf95-45ba669a448e",
             "tenant_id": "903809ded3434f8d89948ee71ca9f5bb",
             "binding:vif_type": "ovs",
             "device_owner": "network:router_interface",
             "binding:capabilities": {"port_filter": True},
             "mac_address": "fa:16:3e:c5:b0:cb", "fixed_ips": [
                 {"subnet_id": "bfa9d0a1-9efb-4bff-bd2b-c103c053560f",
                  "ip_address": "10.0.0.1"}],
             "id": "27193ae1-142a-436c-ab41-c77b1df032a1",
             "security_groups": [],
             "device_id": "6c4d4e32-3667-4cd4-84ea-4cc1e98d18be"}]}
