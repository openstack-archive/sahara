# Copyright (c) 2015 Red Hat, Inc.
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

from sahara.tests.unit import base as testbase
from sahara.utils.openstack import swift


class SwiftClientTest(testbase.SaharaTestCase):

    @mock.patch('sahara.swift.swift_helper.retrieve_tenant')
    @mock.patch('sahara.swift.utils.retrieve_auth_url')
    @mock.patch('swiftclient.Connection')
    def test_client(self, swift_connection, retrieve_auth_url,
                    retrieve_tenant):
        swift.client('testuser', '12345')
        self.assertEqual(1, swift_connection.call_count)

    @mock.patch('sahara.utils.openstack.base.url_for')
    @mock.patch('swiftclient.Connection')
    @mock.patch('sahara.utils.openstack.keystone.token_from_auth')
    @mock.patch('sahara.utils.openstack.keystone.auth_for_proxy')
    def test_client_with_trust(self, auth_for_proxy, token_from_auth,
                               swift_connection, url_for):
        swift.client('testuser', '12345', 'test_trust')
        self.assertEqual(1, auth_for_proxy.call_count)
        self.assertEqual(1, token_from_auth.call_count)
        self.assertEqual(1, swift_connection.call_count)
