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

from savanna.service import api
from savanna.service.validations import clusters as c
from savanna.tests.unit.service.validation import utils as u


class TestClusterCreateValidation(u.ValidationTestCase):
    def setUp(self):
        self._create_object_fun = c.check_cluster_create
        self.scheme = c.CLUSTER_SCHEMA
        api.plugin_base.setup_plugins()

    def test_cluster_create_v_plugin_vers(self):
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'vanilla',
                'hadoop_version': '1'
            },
            bad_req_i=(1, "INVALID_REFERENCE",
                       "Requested plugin 'vanilla' "
                       "doesn't support version '1'"),
        )

    def test_cluster_create_v_required(self):
        self._assert_create_object_validation(
            data={},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name' is a required property")
        )
        self._assert_create_object_validation(
            data={
                'name': 'test-name'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'plugin_name' is a required property")
        )
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'vanilla'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'hadoop_version' is a required property")
        )

    def test_cluster_create_v_types(self):
        data = {
            'name': "testname",
            'plugin_name': "vanilla",
            'hadoop_version': "1.1.2"
        }
        self._assert_types(data)

    def test_cluster_create_v_name_base(self):
        data = {
            'name': "testname",
            'plugin_name': "vanilla",
            'hadoop_version': "1.1.2"
        }
        self._assert_object_name_validation(data, 'hostname')

    def test_cluster_create_v_unique_cl(self):
        data = {
            'name': 'test',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.1.2'
        }
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, 'NAME_ALREADY_EXISTS',
                       "Cluster with name 'test' already exists")
        )

    def test_cluster_create_v_keypair_exists(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'user_keypair_id': 'wrong_keypair'
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Requested keypair 'wrong_keypair' not found")
        )

    def test_cluster_create_v_keypair_type(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'user_keypair_id': '1'
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "'1' is not a 'valid_name'")
        )
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'user_keypair_id': '!'},
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "'!' is not a 'valid_name'")
        )

    def test_cluster_create_v_image_exists(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'default_image_id': '550e8400-e29b-41d4-a616-446655440000'
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Requested image '550e8400-e29b-41d4-a616-446655440000'"
                       " is not registered")
        )

    def test_cluster_create_v_plugin_name_exists(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "wrong_plugin",
                'hadoop_version': "1.1.2",
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Savanna doesn't contain plugin "
                       "with name 'wrong_plugin'")
        )

    def test_cluster_create_v_cluster_configs(self):
        self._assert_cluster_configs_validation()

    def test_cluster_create_v_right_data(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'user_keypair_id': 'test_keypair',
                'cluster_configs': {
                    'HDFS': {
                        u'hadoop.tmp.dir': '/temp/'
                    }
                },
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
            }
        )

    def test_cluster_create_v_default_image_required_tags(self):
        self._assert_cluster_default_image_tags_validation()
