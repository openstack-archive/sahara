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
import unittest2

from savanna import context
import savanna.swift.swift_helper as h

GENERAL_PREFIX = "fs.swift."
SERVICE_PREFIX = "service.savanna."

GENERAL = ["impl", "connect.timeout", "socket.timeout",
           "connect.retry.count", "connect.throttle.delay",
           "blocksize", "partsize", "requestsize"]

SERVICE_SPECIFIC = ["auth.url", "tenant",
                    "username", "password", "http.port",
                    "https.port", "public", "location-aware",
                    "region", "apikey"]


class SwiftIntegrationTestCase(unittest2.TestCase):
    def setUp(self):
        context.set_ctx(
            context.Context('test_user', 'test_tenant', 'test_auth_token',
                            {'X-Tenant-Name': "test_tenant"}))

    @mock.patch('savanna.swift.swift_helper._retrieve_auth_url')
    def test_get_swift_configs(self, authUrlConfig):
        authUrlConfig.return_value = "http://localhost:8080/v2.0/tokens"

        result = h.get_swift_configs()
        self.assertEqual(7, len(result))
        self.assertIn({'name': "fs.swift.service.savanna.location-aware",
                       'value': 'true', 'description': ''}, result)
        self.assertIn({'name': "fs.swift.service.savanna.tenant",
                       'value': 'test_tenant', 'description': ''}, result)
        self.assertIn({'name': "fs.swift.service.savanna.http.port",
                       'value': '8080', 'description': ''}, result)
