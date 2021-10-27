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

import six
import testtools

from sahara import exceptions
from sahara.service.api import v10 as api
from sahara.service.validations import clusters as c
from sahara.service.validations import clusters_schema as c_schema
from sahara.tests.unit import base
from sahara.tests.unit.service.validation import utils as u


class TestClusterCreateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestClusterCreateValidation, self).setUp()
        self._create_object_fun = c.check_cluster_create
        self.scheme = c_schema.CLUSTER_SCHEMA
        api.plugin_base.setup_plugins()

    def test_cluster_create_v_plugin_vers(self):
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'fake',
                'hadoop_version': '1'
            },
            bad_req_i=(1, "INVALID_REFERENCE",
                       "Requested plugin 'fake' "
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
                'plugin_name': 'fake'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'hadoop_version' is a required property")
        )

    def test_cluster_create_v_types(self):
        data = {
            'name': "testname",
            'plugin_name': "fake",
            'hadoop_version': "0.1"
        }
        self._assert_types(data)

    def test_cluster_create_v_name_base(self):
        data = {
            'name': "testname",
            'plugin_name': "fake",
            'hadoop_version': "0.1"
        }
        self._assert_valid_name_hostname_validation(data)

    def test_cluster_create_v_unique_cl(self):
        data = {
            'name': 'test',
            'plugin_name': 'fake',
            'hadoop_version': '0.1'
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
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': 'wrong_keypair'
            },
            bad_req_i=(1, 'NOT_FOUND',
                       "Requested keypair 'wrong_keypair' not found")
        )

    def test_cluster_create_v_keypair_type(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': '!'},
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "user_keypair_id: '!' is not a 'valid_keypair_name'")
        )

    def test_cluster_create_v_image_exists(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
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
                'hadoop_version': "0.1",
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Sahara doesn't contain plugin "
                       "with name 'wrong_plugin'")
        )

    def test_cluster_create_v_wrong_network(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': '53a36917-ab9f-4589-'
                                              '94ce-b6df85a68332'
            },
            bad_req_i=(1, 'NOT_FOUND', "Network 53a36917-ab9f-4589-"
                                       "94ce-b6df85a68332 not found")
        )

    def test_cluster_create_v_missing_network(self):
        self._assert_create_object_validation(
            data={
                'name': "test-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
            },
            bad_req_i=(1, 'NOT_FOUND',
                       "'neutron_management_network' field is not found")
        )

    def test_cluster_create_v_long_instance_names(self):
        self._assert_create_object_validation(
            data={
                'name': "long-long-cluster-name",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        "name": "long-long-long-very-long-node-group-name",
                        "node_processes": ["namenode"],
                        "flavor_id": "42",
                        "count": 100,
                    }
                ]
            },
            bad_req_i=(1, 'INVALID_DATA',
                       "Composite hostname long-long-cluster-name-long-long-"
                       "long-very-long-node-group-name-100.novalocal "
                       "in provisioned cluster exceeds maximum limit 64 "
                       "characters")
        )

    def test_cluster_create_v_cluster_configs(self):
        self._assert_cluster_configs_validation(True)

    def test_cluster_create_v_right_data(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': 'test_keypair',
                'cluster_configs': {
                    'general': {
                        'Enable NTP service': True
                    }
                },
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca'
            }
        )

    def test_cluster_create_v_default_image_required_tags(self):
        self._assert_cluster_default_image_tags_validation()

    def test_cluster_create_security_groups(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        "name": "nodegroup",
                        "node_processes": ["namenode"],
                        "flavor_id": "42",
                        "count": 100,
                        'security_groups': ['group1', 'group2'],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca'
                    }
                ]
            }
        )

    def test_cluster_create_missing_floating_pool(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        "name": "ng1",
                        "node_processes": ["namenode"],
                        "flavor_id": "42",
                        "count": 100,
                        'security_groups': ['group1', 'group2'],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca'
                    },
                    {
                        "name": "ng2",
                        "node_processes": ["datanode"],
                        "flavor_id": "42",
                        "count": 100,
                        'security_groups': ['group1', 'group2']
                    }
                ]
            }
        )

    def test_cluster_create_with_proxy_gateway(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        "name": "ng1",
                        "node_processes": ["namenode"],
                        "flavor_id": "42",
                        "count": 100,
                        'security_groups': ['group1', 'group2'],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca',
                        "is_proxy_gateway": True
                    },
                    {
                        "name": "ng2",
                        "node_processes": ["datanode"],
                        "flavor_id": "42",
                        "count": 100,
                        'security_groups': ['group1', 'group2']
                    }
                ]
            }
        )

    def test_cluster_create_security_groups_by_ids(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        "name": "nodegroup",
                        "node_processes": ["namenode"],
                        "flavor_id": "42",
                        "count": 100,
                        'security_groups': ['2', '3'],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca'
                    }
                ]
            }
        )

    def test_cluster_missing_security_groups(self):
        self._assert_create_object_validation(
            data={
                'name': "testname",
                'plugin_name': "fake",
                'hadoop_version': "0.1",
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        "name": "nodegroup",
                        "node_processes": ["namenode"],
                        "flavor_id": "42",
                        "count": 100,
                        'security_groups': ['group1', 'group3'],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca'
                    }
                ]
            },
            bad_req_i=(1, 'NOT_FOUND',
                       "Security group 'group3' not found")
        )

    def test_cluster_create_availability_zone(self):
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'fake',
                'hadoop_version': '0.1',
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        'name': 'nodegroup',
                        'node_processes': ['namenode'],
                        'flavor_id': '42',
                        'count': 100,
                        'security_groups': [],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca',
                        'availability_zone': 'nova',
                        'volumes_per_node': 1,
                        'volumes_size': 1,
                        'volumes_availability_zone': 'nova'
                    }
                ]
            }
        )

    def test_cluster_create_wrong_availability_zone(self):
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'fake',
                'hadoop_version': '0.1',
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        'name': 'nodegroup',
                        'node_processes': ['namenode'],
                        'flavor_id': '42',
                        'count': 100,
                        'security_groups': [],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca',
                        'availability_zone': 'nonexistent'
                    }
                ]
            },
            bad_req_i=(1, 'NOT_FOUND',
                       "Nova availability zone 'nonexistent' not found")
        )

    def test_cluster_create_wrong_volumes_availability_zone(self):
        self._assert_create_object_validation(
            data={
                'name': 'testname',
                'plugin_name': 'fake',
                'hadoop_version': '0.1',
                'user_keypair_id': 'test_keypair',
                'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
                'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                              '9a93-aa048022c1ca',
                'node_groups': [
                    {
                        'name': 'nodegroup',
                        'node_processes': ['namenode'],
                        'flavor_id': '42',
                        'count': 100,
                        'security_groups': [],
                        'floating_ip_pool':
                            'd9a3bebc-f788-4b81-9a93-aa048022c1ca',
                        'volumes_per_node': 1,
                        'volumes_availability_zone': 'nonexistent'
                    }
                ]
            },
            bad_req_i=(1, 'NOT_FOUND',
                       "Cinder availability zone 'nonexistent' not found")
        )


class TestClusterCreateFlavorValidation(base.SaharaWithDbTestCase):
    """Tests for valid flavor on cluster create.

    The following use cases for flavors during cluster create are validated:
      * Flavor id defined in a node group template and used in a cluster
        template.
      * Flavor id defined in node groups on cluster create.
      * Both node groups and cluster template defined on cluster create.
      * Node groups with node group template defined on cluster create.
    """

    def setUp(self):
        super(TestClusterCreateFlavorValidation, self).setUp()
        self.override_config('plugins', ['fake'])
        modules = [
            "sahara.service.validations.base.check_plugin_name_exists",
            "sahara.service.validations.base.check_plugin_supports_version",
            "sahara.service.validations.base._get_plugin_configs",
            "sahara.service.validations.base.check_node_processes",
        ]
        self.patchers = []
        for module in modules:
            patch = mock.patch(module)
            patch.start()
            self.patchers.append(patch)

        nova_p = mock.patch("sahara.utils.openstack.nova.client")
        nova = nova_p.start()
        self.patchers.append(nova_p)
        nova().flavors.list.side_effect = u._get_flavors_list
        api.plugin_base.setup_plugins()

    def tearDown(self):
        u.stop_patch(self.patchers)
        super(TestClusterCreateFlavorValidation, self).tearDown()

    def _create_node_group_template(self, flavor='42'):
        ng_tmpl = {
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "node_processes": ["namenode"],
            "name": "master",
            "flavor_id": flavor
        }
        return api.create_node_group_template(ng_tmpl).id

    def _create_cluster_template(self, ng_id):
        cl_tmpl = {
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "node_groups": [
                {"name": "master",
                 "count": 1,
                 "node_group_template_id": "%s" % ng_id}
            ],
            "name": "test-template"
        }
        return api.create_cluster_template(cl_tmpl).id

    def test_cluster_create_v_correct_flavor(self):
        ng_id = self._create_node_group_template(flavor='42')
        ctmpl_id = self._create_cluster_template(ng_id)

        data = {
            "name": "testname",
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "cluster_template_id": '%s' % ctmpl_id,
            "neutron_management_network": "d9a3bebc-f788-4b81-"
                                          "9a93-aa048022c1ca",
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
        }
        patchers = u.start_patch(False)
        c.check_cluster_create(data)
        u.stop_patch(patchers)

        data1 = {
            "name": "testwithnodegroups",
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "neutron_management_network": "d9a3bebc-f788-4b81-"
                                          "9a93-aa048022c1ca",
            "node_groups": [
                {
                    "name": "allinone",
                    "count": 1,
                    "flavor_id": "42",
                    "node_processes": [
                        "namenode",
                        "jobtracker",
                        "datanode",
                        "tasktracker"
                    ]
                }
            ],
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
        }
        patchers = u.start_patch(False)
        c.check_cluster_create(data1)
        u.stop_patch(patchers)

    def test_cluster_create_v_invalid_flavor(self):
        ng_id = self._create_node_group_template(flavor='10')
        ctmpl_id = self._create_cluster_template(ng_id)

        data = {
            "name": "testname",
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "cluster_template_id": '%s' % ctmpl_id,
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
        }
        data1 = {
            "name": "testwithnodegroups",
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "neutron_management_network": "d9a3bebc-f788-4b81-"
                                          "9a93-aa048022c1ca",
            "node_groups": [
                {
                    "name": "allinone",
                    "count": 1,
                    "flavor_id": "10",
                    "node_processes": [
                        "namenode",
                        "resourcemanager",
                        "datanode",
                        "nodemanager"
                    ]
                }
            ],
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
        }
        for values in [data, data1]:
            with testtools.ExpectedException(
                    exceptions.NotFoundException):
                patchers = u.start_patch(False)
                try:
                    c.check_cluster_create(values)
                except exceptions.NotFoundException as e:
                    message = six.text_type(e).split('\n')[0]
                    self.assertEqual("Requested flavor '10' not found",
                                     message)
                    raise e
                finally:
                    u.stop_patch(patchers)

    def test_cluster_create_cluster_tmpl_node_group_mixin(self):
        ng_id = self._create_node_group_template(flavor='10')
        ctmpl_id = self._create_cluster_template(ng_id)

        data = {
            "name": "testtmplnodegroups",
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "cluster_template_id": '%s' % ctmpl_id,
            "neutron_management_network": "d9a3bebc-f788-4b81-"
                                          "9a93-aa048022c1ca",
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
            "node_groups": [
                {
                    "name": "allinone",
                    "count": 1,
                    "flavor_id": "42",
                    "node_processes": [
                        "namenode",
                        "resourcemanager",
                        "datanode",
                        "nodemanager"
                    ]
                }
            ]
        }
        patchers = u.start_patch(False)
        c.check_cluster_create(data)
        u.stop_patch(patchers)

    def test_cluster_create_node_group_tmpl_mixin(self):
        ng_id = self._create_node_group_template(flavor='23')
        data = {
            "name": "testtmplnodegroups",
            "plugin_name": "fake",
            "hadoop_version": "0.1",
            "neutron_management_network": "d9a3bebc-f788-4b81-"
                                          "9a93-aa048022c1ca",
            "node_groups": [
                {
                    "node_group_template_id": '%s' % ng_id,
                    "name": "allinone",
                    "count": 1,
                    "flavor_id": "42",
                    "node_processes": [
                        "namenode",
                        "resourcemanager",
                        "datanode",
                        "nodemanager"
                    ]
                },
            ],
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
        }
        with testtools.ExpectedException(exceptions.NotFoundException):
            patchers = u.start_patch(False)
            try:
                c.check_cluster_create(data)
            except exceptions.NotFoundException as e:
                message = six.text_type(e).split('\n')[0]
                self.assertEqual("Requested flavor '23' not found",
                                 message)
                raise e
            finally:
                u.stop_patch(patchers)
