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


from unittest import mock

from oslo_utils import uuidutils

from sahara.service.api import v10 as api
from sahara.service.validations import cluster_template_schema as ct_schema
from sahara.service.validations import cluster_templates as ct
from sahara.tests.unit.service.validation import utils as u


class TestClusterTemplateCreateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestClusterTemplateCreateValidation, self).setUp()
        self._create_object_fun = ct.check_cluster_template_create
        self.scheme = ct_schema.CLUSTER_TEMPLATE_SCHEMA
        api.plugin_base.setup_plugins()

    def test_cluster_template_create_v_cluster_configs(self):
        self._assert_cluster_configs_validation()

    def test_cluster_template_create_v_ng(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'node_groups': [
                    {'name': 'a'}
                ]
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "node_groups[0]: {'name': 'a'} is not valid under "
                       "any of the given schemas")
        )
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'node_groups': [
                    {'name': 'a',
                     'flavor_id': '42'}
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "node_groups[0]: {'name': 'a', 'flavor_id': '42'} "
                       "is not valid under any of the given schemas")

        )
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'node_groups': [
                    {'name': 'a',
                     'flavor_id': '42',
                     'node_processes': ['namenode']}
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "node_groups[0]: {'node_processes': ['namenode'], "
                       "'name': 'a', "
                       "'flavor_id': '42'} "
                       "is not valid under any of the given schemas")
        )
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'node_groups': [
                    {
                        'name': 'a',
                        'flavor_id': '42',
                        'node_processes': ['namenode'],
                        'count': 1
                    },
                    {
                        "node_group_template_id": "550e8400-e29b-41d4-a716-"
                                                  "446655440000",
                        "name": "a",
                        'count': 2
                    }
                ]
            },
            bad_req_i=(1, "INVALID_DATA",
                       "Duplicates in node group names are detected")
        )

    def test_cluster_template_create_v_ng_templates(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'node_groups': [
                    {
                        "node_group_template_id": "",
                        "name": "test",
                    }
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "node_groups[0]: {'node_group_template_id': '', "
                       "'name': 'test'} "
                       "is not valid under any of the given schemas")

        )
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'node_groups': [
                    {
                        "node_group_template_id": "test",
                        "name": "test",
                        'count': 3
                    }
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "node_groups[0]: {'count': 3, "
                       "'node_group_template_id': 'test', "
                       "'name': 'test'} "
                       "is not valid under any of the given schemas")

        )

    def test_cluster_template_create_v_ng_templates_right(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'node_groups': [
                    {
                        "node_group_template_id": "550e8400-e29b-41d4-a716-"
                                                  "446655440000",
                        "name": "test",
                        'count': 3
                    }
                ],
                'domain_name': 'domain.org.'
            },

        )

    def test_cluster_template_create_v_name_base(self):
        data = {
            'name': "testname",
            'plugin_name': "fake",
            'hadoop_version': "0.1"
        }
        self._assert_valid_name_hostname_validation(data)

    def test_cluster_template_create_v_types(self):
        data = {
            'name': "testname",
            'plugin_name': "fake",
            'hadoop_version': "0.1"
        }
        self._assert_types(data)

    def test_cluster_template_create_v_required(self):
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
                'plugin_name': 'fake'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'hadoop_version' is a required property")
        )

    @mock.patch("sahara.service.validations.base.check_all_configurations")
    @mock.patch("sahara.service.validations.base.check_network_exists")
    @mock.patch("sahara.service.validations.base.check_required_image_tags")
    @mock.patch("sahara.service.validations.base.check_image_registered")
    def test_cluster_template_create_v_right(self, image_reg, image_tags,
                                             net_exists, all_configs):
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'fake',
                'hadoop_version': '0.1',
                'default_image_id': uuidutils.generate_uuid(),
                'cluster_configs': {
                    "service_1": {
                        "config_1": "value_1"
                    }
                },
                'node_groups': [
                    {
                        "node_group_template_id": "550e8400-e29b-41d4-a716-"
                                                  "446655440000",
                        "name": "charlie",
                        'count': 3
                    }
                ],
                'anti_affinity': ['datanode'],
                'description': 'my template',
                'neutron_management_network': uuidutils.generate_uuid(),
                'domain_name': 'domain.org.'
            })

    @mock.patch("sahara.service.validations.base.check_network_exists")
    @mock.patch("sahara.service.validations.base.check_required_image_tags")
    @mock.patch("sahara.service.validations.base.check_image_registered")
    def test_cluster_template_create_v_right_nulls(self, image_reg, image_tags,
                                                   net_exists):
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'fake',
                'hadoop_version': '0.1',
                'default_image_id': None,
                'cluster_configs': None,
                'node_groups': None,
                'anti_affinity': None,
                'description': None,
                'neutron_management_network': None,
                'domain_name': None
            })

    def test_cluster_template_create_v_plugin_name_exists(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "wrong_plugin",
                'hadoop_version': "0.1",
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Sahara doesn't contain plugin "
                       "with name 'wrong_plugin'")
        )

    def test_cluster_template_create_v_unique_cl(self):
        data = {
            'name': 'test',
            'plugin_name': 'fake',
            'hadoop_version': '0.1'
        }
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, 'NAME_ALREADY_EXISTS',
                       "Cluster template with name 'test' already exists")
        )

    def test_cluster_template_wrong_neutron_mngmt_net(self):
        data = {
            'name': 'test-template',
            'plugin_name': 'fake',
            'hadoop_version': '0.1',
            'neutron_management_network': '53a36917-ab9f-4589'
                                          '-94ce-b6df85a68332'
        }
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, 'NOT_FOUND', "Network 53a36917-ab9f-4589-"
                                       "94ce-b6df85a68332 not found")
        )

    def test_cluster_create_v_default_image_required_tags(self):
        self._assert_cluster_default_image_tags_validation()
