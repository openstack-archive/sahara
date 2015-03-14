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

from sahara.service import api
from sahara.service.validations import node_group_template_schema as ngt_schema
from sahara.service.validations import node_group_templates as nt
from sahara.tests.unit.service.validation import utils as u


class TestNGTemplateCreateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestNGTemplateCreateValidation, self).setUp()
        self._create_object_fun = nt.check_node_group_template_create
        self.scheme = ngt_schema.NODE_GROUP_TEMPLATE_SCHEMA
        api.plugin_base.setup_plugins()

    def test_node_groups_create_required(self):
        self._assert_create_object_validation(
            data={
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name' is a required property")
        )
        self._assert_create_object_validation(
            data={
                'name': 'a'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'flavor_id' is a required property")
        )
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'hadoop_version' is a required property")
        )
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'node_processes' is a required property")
        )
        self._assert_create_object_validation(
            data={
                'name': "a",
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': []
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'\[\] is too short')
        )

    def test_ng_template_create_v_names(self):
        data = {
            'name': 'a',
            'flavor_id': '42',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.2.1',
            'node_processes': ['namenode']
        }
        self._assert_valid_name_hostname_validation(data)

    def test_ng_template_create_v_node_processes(self):
        self._assert_create_object_validation(
            data={
                'name': "a",
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ["namenode", "namenode"]
            },
            bad_req_i=(1, 'INVALID_DATA',
                       'Duplicates in node processes have been detected')
        )
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['wrong_process']
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin doesn't support the following node processes: "
                       "['wrong_process']")
        )

    def test_ng_template_create_v_right(self):
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['namenode',
                                   'datanode',
                                   'secondarynamenode',
                                   'tasktracker',
                                   'jobtracker'],
                'node_configs': {
                    'HDFS': {
                        u'hadoop.tmp.dir': '/temp/'
                    }
                },
                'image_id': '550e8400-e29b-41d4-a716-446655440000',
                'volumes_per_node': 2,
                'volumes_size': 10,
                'description': 'test node template',
                'floating_ip_pool': 'd9a3bebc-f788-4b81-9a93-aa048022c1ca'
            }
        )

    def test_ng_template_create_v_minimum_ints(self):
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['wrong_process'],
                'volumes_per_node': -1
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'-1(.0)? is less than the minimum of 0')
        )
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['wrong_process'],
                'volumes_size': 0
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'0(.0)? is less than the minimum of 1')
        )

    def test_ng_template_create_v_types(self):
        default_data = {
            'name': 'a', 'flavor_id': '42',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.2.1',
            'node_processes': ['namenode']
        }
        self._assert_types(default_data)

    def test_ng_template_create_v_unique_ng(self):
        data = {
            'name': 'test',
            'flavor_id': '42',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.2.1',
            'node_processes': ['namenode']}
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, 'NAME_ALREADY_EXISTS',
                       "NodeGroup template with name 'test' already exists")
        )

    def test_ng_template_create_v_flavor_exists(self):
        self._assert_create_object_validation(
            data={
                'name': 'test-ng',
                'flavor_id': '1',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['namenode']
            },
            bad_req_i=(1, 'NOT_FOUND',
                       "Requested flavor '1' not found")
        )

    def test_ng_template_create_v_ng_configs(self):
        self._assert_create_object_validation(
            data={
                'name': 'test-ng',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['namenode'],
                'node_configs': {
                    'wrong_target': {
                        u'hadoop.tmp.dir': '/temp/'
                    }
                }},
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin doesn't contain applicable "
                       "target 'wrong_target'")
        )
        self._assert_create_object_validation(
            data={
                'name': 'test-ng',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['namenode'],
                'node_configs': {
                    'HDFS': {
                        's': 'a'
                    }
                }
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin's applicable target 'HDFS' doesn't "
                       "contain config with name 's'")
        )

    def test_ng_template_cinder(self):
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['wrong_process'],
                'volumes_per_node': -1
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'-1(.0)? is less than the minimum of 0')
        )
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['wrong_process'],
                'volumes_size': 0
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'0(.0)? is less than the minimum of 1')
        )
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['datanode', 'tasktracker'],
                'volumes_per_node': 1,
                'volumes_size': 1,
                'volume_mount_prefix': '/mnt/volume'
            }
        )
        data = {
            'name': 'a',
            'flavor_id': '42',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.2.1',
            'node_processes': ['datanode', 'tasktracker'],
            'volumes_per_node': 1,
            'volumes_size': 1,
            'volume_mount_prefix': 'qwerty'
        }
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR', "'qwerty' is not a 'posix_path'")
        )

    def test_wrong_floating_ip_pool(self):
        self._assert_create_object_validation(
            data={
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.2.1',
                'node_processes': ['datanode', 'tasktracker'],
                'floating_ip_pool': 'network_bad'
            },
            bad_req_i=(1, 'NOT_FOUND', "Floating IP pool network_bad "
                                       "not found")
        )
