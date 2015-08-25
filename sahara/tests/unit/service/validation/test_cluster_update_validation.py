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

from sahara.service import api
from sahara.service.validations import clusters_schema as c_schema
from sahara.tests.unit.service.validation import utils as u


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
            'is_protected': False
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
                'is_protected': False
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
