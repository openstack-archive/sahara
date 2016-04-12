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
import testtools

from sahara import exceptions as ex
from sahara.service.validations import clusters as c_val
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
