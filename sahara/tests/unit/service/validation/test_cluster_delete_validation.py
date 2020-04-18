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

import testtools
from unittest import mock

from sahara import exceptions as ex
from sahara.service import validation as v
from sahara.service.validations import clusters as c_val
from sahara.service.validations import clusters_schema as c_schema
from sahara.tests.unit.service.validation import utils as u
from sahara.tests.unit import testutils as tu


class TestClusterDeleteValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestClusterDeleteValidation, self).setUp()
        self.setup_context(tenant_id='tenant1')

    @mock.patch('sahara.service.api.v10.get_cluster')
    def test_cluster_delete_when_protected(self, get_cluster_p):
        cluster = tu.create_cluster("cluster1", "tenant1", "fake",
                                    "0.1", ['ng1'], is_protected=True)
        get_cluster_p.return_value = cluster

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                c_val.check_cluster_delete(cluster.id)
            except ex.DeletionFailed as e:
                self.assert_protected_resource_exception(e)
                raise e

    @mock.patch('sahara.service.api.v10.get_cluster')
    def test_public_cluster_delete_from_another_tenant(self, get_cluster_p):
        cluster = tu.create_cluster("cluster1", "tenant2", "fake",
                                    "0.1", ['ng1'], is_public=True)
        get_cluster_p.return_value = cluster

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                c_val.check_cluster_delete(cluster.id)
            except ex.DeletionFailed as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e


class TestClusterDeleteValidationV2(testtools.TestCase):
    @mock.patch("sahara.utils.api.request_data")
    @mock.patch("sahara.utils.api.bad_request")
    def _validate_body(self, request, br, rd):
        m_func = mock.Mock()
        m_func.__name__ = "m_func"

        rd.return_value = request

        validator = v.validate(c_schema.CLUSTER_DELETE_SCHEMA_V2, m_func)
        validator(m_func)(data=request)

        return not br.call_count

    def test_delete_schema_empty_body(self):
        request = {}
        self.assertTrue(self._validate_body(request))

    def test_delete_schema_wrong_type(self):
        request = {"force": "True"}
        self.assertFalse(self._validate_body(request))

    def test_delete_schema_extra_fields(self):
        request = {"force": True, "just_kidding": False}
        self.assertFalse(self._validate_body(request))

    def test_delete_schema_good(self):
        request = {"force": True}
        self.assertTrue(self._validate_body(request))
