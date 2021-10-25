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

import copy

from sahara.service.api import v10 as api
from sahara.service.validations import node_group_template_schema as nt
from sahara.tests.unit.service.validation import utils as u


def empty(data, **kwargs):
    pass


SAMPLE_DATA = {
    'name': 'a',
    'flavor_id': '42',
    'plugin_name': 'fake',
    'hadoop_version': '0.1',
    'node_processes': ['namenode',
                       'datanode',
                       'secondarynamenode',
                       'nodemanager',
                       'resourcemanager'],
    'node_configs': {
        'HDFS': {
            'mapreduce.task.tmp.dir': '/temp/'
        }
    },
    'image_id': '550e8400-e29b-41d4-a716-446655440000',
    'volumes_per_node': 2,
    'volumes_size': 10,
    'description': 'test node template',
    'floating_ip_pool': 'd9a3bebc-f788-4b81-9a93-aa048022c1ca',
    'is_public': False,
    'is_protected': False
}


class TestNGTemplateUpdateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestNGTemplateUpdateValidation, self).setUp()
        self._create_object_fun = empty
        self.scheme = nt.NODE_GROUP_TEMPLATE_UPDATE_SCHEMA
        api.plugin_base.setup_plugins()

    def test_node_groups_update_nothing_required(self):
        self._assert_create_object_validation(
            data={}
        )

    def test_ng_template_update_schema(self):
        create = copy.copy(nt.NODE_GROUP_TEMPLATE_SCHEMA)
        update = copy.copy(nt.NODE_GROUP_TEMPLATE_UPDATE_SCHEMA)

        # No required items for update
        self.assertEqual([], update["required"])

        # Other than required, schemas are equal
        del update["required"]
        del create["required"]
        self.assertEqual(create, update)

    def test_ng_template_update_v(self):

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
