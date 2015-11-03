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
from sahara.service import api
from sahara.service.validations import clusters as c_val
from sahara.service.validations import clusters_schema as c_schema
from sahara.tests.unit.service.validation import utils as u
from sahara.tests.unit import testutils as tu


class TestClusterUpdateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestClusterUpdateValidation, self).setUp()
        self._create_object_fun = mock.Mock()
        self.scheme = c_schema.CLUSTER_UPDATE_SCHEMA
        api.plugin_base.setup_plugins()

    def test_cluster_update_types(self):
        self._assert_types({
            'name': 'cluster',
            'description': 'very big cluster',
            'is_public': False,
            'is_protected': False,
            'shares': []
        })

    def test_cluster_update_nothing_required(self):
        self._assert_create_object_validation(
            data={}
        )

    def test_cluster_update(self):
        self._assert_create_object_validation(
            data={
                'name': 'cluster',
                'description': 'very big cluster',
                'is_public': False,
                'is_protected': False,
                'shares': []
            }
        )

        self._assert_create_object_validation(
            data={
                'name': 'cluster',
                'id': '1'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "Additional properties are not allowed "
                       "('id' was unexpected)")
        )

    @mock.patch('sahara.service.api.get_cluster')
    def test_cluster_update_when_protected(self, get_cluster_p):
        cluster = tu.create_cluster("cluster1", "tenant_1", "fake",
                                    "0.1", ['ng1'], is_protected=True)
        get_cluster_p.return_value = cluster

        # cluster can't be updated if it's marked as protected
        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                c_val.check_cluster_update(cluster.id, {'name': 'new'})
            except ex.UpdateFailedException as e:
                self.assert_protected_resource_exception(e)
                raise e

        # cluster can be updated because is_protected flag was set to False
        c_val.check_cluster_update(
            cluster.id, {'is_protected': False, 'name': 'new'})

    @mock.patch('sahara.service.api.get_cluster')
    def test_public_cluster_update_from_another_tenant(self, get_cluster_p):
        cluster = tu.create_cluster("cluster1", "tenant_2", "fake",
                                    "0.1", ['ng1'], is_public=True)
        get_cluster_p.return_value = cluster

        # cluster can't be updated from another tenant
        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                c_val.check_cluster_update(cluster.id, {'name': 'new'})
            except ex.UpdateFailedException as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e
