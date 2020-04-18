# Copyright (c) 2015 OpenStack Foundation
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

import copy
from unittest import mock


from sahara.service.api import v10 as api
from sahara.service.validations import cluster_template_schema as ct_schema
from sahara.tests.unit.service.validation import utils as u


SAMPLE_DATA = {
    'name': 'testname',
    'plugin_name': 'fake',
    'hadoop_version': '0.1',
    'is_public': False,
    'is_protected': False
}


class TestClusterTemplateUpdateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestClusterTemplateUpdateValidation, self).setUp()
        self._create_object_fun = mock.Mock()
        self.scheme = ct_schema.CLUSTER_TEMPLATE_UPDATE_SCHEMA
        api.plugin_base.setup_plugins()

    def test_cluster_template_update_nothing_required(self):
        self._assert_create_object_validation(
            data={}
        )

    def test_cluster_template_update_schema(self):
        create = copy.copy(ct_schema.CLUSTER_TEMPLATE_SCHEMA)
        update = copy.copy(ct_schema.CLUSTER_TEMPLATE_UPDATE_SCHEMA)

        # No required items for update
        self.assertEqual([], update["required"])

        # Other than required, schemas are equal
        del update["required"]
        del create["required"]
        self.assertEqual(create, update)

    def test_cluster_template_update(self):
        self._assert_create_object_validation(
            data=SAMPLE_DATA
        )

        extra = copy.copy(SAMPLE_DATA)
        extra['dog'] = 'fido'

        self._assert_create_object_validation(
            data=extra,
            bad_req_i=(1, "VALIDATION_ERROR",
                       "Additional properties are not allowed "
                       "('dog' was unexpected)")
        )
