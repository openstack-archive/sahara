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

import webob.dec

from sahara.api.middleware import auth_valid
from sahara.tests.unit import base as test_base


class AuthValidatorTest(test_base.SaharaTestCase):

    @staticmethod
    @webob.dec.wsgify
    def application(req):
        return "Banana"

    def setUp(self):
        super(AuthValidatorTest, self).setUp()
        self.app = auth_valid.AuthValidator(self.application)

    def test_auth_ok(self):
        req = webob.Request.blank("/v1.1/tid/clusters", accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid"})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)

    def test_auth_ok_without_path(self):
        req = webob.Request.blank("/", accept="text/plain", method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid"})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)

    def test_auth_without_header(self):
        req = webob.Request.blank("/v1.1/tid/clusters", accept="text/plain",
                                  method="GET")
        res = req.get_response(self.app)
        self.assertEqual(503, res.status_code)

    def test_auth_with_wrong_url(self):
        req = webob.Request.blank("/v1.1", accept="text/plain", method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid"})
        res = req.get_response(self.app)
        self.assertEqual(404, res.status_code)

    def test_auth_different_tenant(self):
        req = webob.Request.blank("/v1.1/tid1/clusters", accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid2"})
        res = req.get_response(self.app)
        self.assertEqual(401, res.status_code)


class AuthValidatorV2Test(test_base.SaharaTestCase):

    @staticmethod
    @webob.dec.wsgify
    def application(req):
        return "Banana"

    def setUp(self):
        super(AuthValidatorV2Test, self).setUp()
        self.app = auth_valid.AuthValidatorV2(self.application)

    def test_auth_ok(self):
        req = webob.Request.blank("/v2/tid/clusters", accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid"},
                                  headers={"OpenStack-Project-ID": "tid"})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)

    def test_auth_ok_without_path(self):
        req = webob.Request.blank("/", accept="text/plain", method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid"},
                                  headers={"OpenStack-Project-ID": "tid"})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)

    def test_auth_without_header(self):
        req = webob.Request.blank("/v2/tid/clusters", accept="text/plain",
                                  method="GET")
        res = req.get_response(self.app)
        self.assertEqual(503, res.status_code)

    def test_auth_with_wrong_url(self):
        req = webob.Request.blank("/v2", accept="text/plain", method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid"})
        res = req.get_response(self.app)
        self.assertEqual(404, res.status_code)

    def test_auth_different_tenant(self):
        req = webob.Request.blank("/v2/tid1/clusters", accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": "tid2"},
                                  headers={"OpenStack-Project-ID": "tid"})
        res = req.get_response(self.app)
        self.assertEqual(401, res.status_code)
