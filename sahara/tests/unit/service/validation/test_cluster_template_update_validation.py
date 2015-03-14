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

from sahara.service import api
from sahara.service.validations import cluster_template_schema as ct_schema
from sahara.service.validations import cluster_templates as ct
from sahara.tests.unit.service.validation import utils as u


SAMPLE_DATA = {
    'name': 'testname',
    'plugin_name': 'vanilla',
    'hadoop_version': '1.2.1'
}


class TestClusterTemplateUpdateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestClusterTemplateUpdateValidation, self).setUp()
        self._create_object_fun = ct.check_cluster_template_update
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
        self.assertEqual(update["required"], [])

        # Other than required, schemas are equal
        del update["required"]
        del create["required"]
        self.assertEqual(update, create)

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
