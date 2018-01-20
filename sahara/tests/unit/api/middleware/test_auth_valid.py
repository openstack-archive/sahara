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

    tid1 = '8f9f0c8c4c634d6280e785b44a10b8ab'
    tid2 = '431c8ab1f14f4607bdfc17e05b3924d1'

    @staticmethod
    @webob.dec.wsgify
    def application(req):
        return "Banana"

    def setUp(self):
        super(AuthValidatorTest, self).setUp()
        self.app = auth_valid.AuthValidator(self.application)

    def test_auth_ok_project_id_in_url(self):
        req = webob.Request.blank("/v1.1/%s/clusters" % self.tid1,
                                  accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": self.tid1})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)

    def test_auth_ok_no_project_id_in_url(self):
        req = webob.Request.blank("/v1.1/clusters",
                                  accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": self.tid1})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)

    def test_auth_ok_without_path(self):
        req = webob.Request.blank("/", accept="text/plain", method="GET",
                                  environ={"HTTP_X_TENANT_ID": self.tid1})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)

    def test_auth_without_environ(self):
        req = webob.Request.blank("/v1.1/%s/clusters" % self.tid1,
                                  accept="text/plain",
                                  method="GET")
        res = req.get_response(self.app)
        self.assertEqual(503, res.status_code)

    def test_auth_with_wrong_url(self):
        req = webob.Request.blank("/v1.1", accept="text/plain", method="GET",
                                  environ={"HTTP_X_TENANT_ID": self.tid1})
        res = req.get_response(self.app)
        self.assertEqual(404, res.status_code)

    def test_auth_different_tenant(self):
        req = webob.Request.blank("/v1.1/%s/clusters" % self.tid1,
                                  accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": self.tid2})
        res = req.get_response(self.app)
        self.assertEqual(401, res.status_code)

    def test_auth_tenant_id_in_url_v2(self):
        # NOTE(jfreud): we expect AuthValidator to let this case pass through
        # although Flask will reject it with a 404 further down the pipeline
        req = webob.Request.blank("/v2/%s/clusters" % self.tid1,
                                  accept="text/plain",
                                  method="GET",
                                  environ={"HTTP_X_TENANT_ID": self.tid1})
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)
