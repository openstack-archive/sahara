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

from sahara.service import direct_engine
from sahara.tests.unit import base
from sahara.utils import general as g


class TestDirectEngine(base.SaharaWithDbTestCase):

    @mock.patch('sahara.utils.openstack.nova.client')
    def test_delete_auto_security_group(self, nova_client):
        engine = direct_engine.DirectEngine()
        ng = mock.Mock(id="16fd2706-8baf-433b-82eb-8c7fada847da",
                       auto_security_group=True)
        ng.name = "ngname"
        ng.cluster.name = "cluster"
        auto_name = g.generate_auto_security_group_name(ng)
        ng.security_groups = [auto_name]

        client = mock.Mock()
        nova_client.return_value = client

        client.security_groups.get.side_effect = lambda x: SecurityGroup(x)

        engine._delete_auto_security_group(ng)

        client.security_groups.delete.assert_called_once_with(auto_name)

    @mock.patch('sahara.utils.openstack.nova.client')
    def test_delete_auto_security_group_other_groups(self, nova_client):
        engine = direct_engine.DirectEngine()
        ng = mock.Mock(id="16fd2706-8baf-433b-82eb-8c7fada847da",
                       auto_security_group=True)
        ng.name = "ngname"
        ng.cluster.name = "cluster"
        auto_name = g.generate_auto_security_group_name(ng)
        ng.security_groups = ['1', '2', auto_name]

        client = mock.Mock()
        nova_client.return_value = client

        client.security_groups.get.side_effect = lambda x: SecurityGroup(x)

        engine._delete_auto_security_group(ng)

        client.security_groups.delete.assert_called_once_with(auto_name)

    @mock.patch('sahara.utils.openstack.nova.client')
    def test_delete_auto_security_group_no_groups(self, nova_client):
        engine = direct_engine.DirectEngine()
        ng = mock.Mock(id="16fd2706-8baf-433b-82eb-8c7fada847da",
                       auto_security_group=True)
        ng.name = "ngname"
        ng.cluster.name = "cluster"
        ng.security_groups = []

        client = mock.Mock()
        nova_client.return_value = client

        client.security_groups.get.side_effect = lambda x: SecurityGroup(x)

        engine._delete_auto_security_group(ng)

        self.assertEqual(0, client.security_groups.delete.call_count)

    @mock.patch('sahara.utils.openstack.nova.client')
    def test_delete_auto_security_group_wrong_group(self, nova_client):
        engine = direct_engine.DirectEngine()
        ng = mock.Mock(id="16fd2706-8baf-433b-82eb-8c7fada847da",
                       auto_security_group=True)
        ng.name = "ngname"
        ng.cluster.name = "cluster"
        ng.security_groups = ['1', '2']

        client = mock.Mock()
        nova_client.return_value = client

        client.security_groups.get.side_effect = lambda x: SecurityGroup(x)

        engine._delete_auto_security_group(ng)

        self.assertEqual(0, client.security_groups.delete.call_count)


class SecurityGroup(object):
    def __init__(self, name):
        super(SecurityGroup, self).__init__()
        self.name = name
