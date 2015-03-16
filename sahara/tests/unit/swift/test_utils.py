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

from sahara.swift import utils
from sahara.tests.unit import base as testbase


class SwiftUtilsTest(testbase.SaharaTestCase):

    def setUp(self):
        super(SwiftUtilsTest, self).setUp()
        self.override_config('use_identity_api_v3', True)

    @mock.patch('sahara.utils.openstack.base.url_for')
    def test_retrieve_auth_url(self, url_for_mock):
        correct = "https://127.0.0.1:8080/v2.0/"

        def _assert(uri):
            url_for_mock.return_value = uri
            self.assertEqual(correct, utils.retrieve_auth_url())

        _assert("%s/" % correct)
        _assert("https://127.0.0.1:8080")
        _assert("https://127.0.0.1:8080/")
        _assert("https://127.0.0.1:8080/v2.0")
        _assert("https://127.0.0.1:8080/v2.0/")
        _assert("https://127.0.0.1:8080/v42/")
        _assert("https://127.0.0.1:8080/foo")
