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

from sahara import exceptions as ex
from sahara.plugins.fake import plugin
from sahara.service.api import v10 as api
import sahara.service.validation as v
from sahara.service.validations import clusters_scaling as c_s
from sahara.service.validations import clusters_schema as c_schema
from sahara.tests.unit.service.validation import utils as u
from sahara.tests.unit import testutils as tu
from sahara.utils import cluster as c_u


def _get_plugin(plugin_name):
    if plugin_name == 'fake':
        return plugin.FakePluginProvider()
    return None


class TestScalingValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestScalingValidation, self).setUp()
        api.plugin_base.setup_plugins()
        self._create_object_fun = mock.Mock()
        self.duplicates_detected = ("Duplicates in node group names are"
                                    " detected: ['a']")
        self.setup_context(tenant_id='tenant1')

    @mock.patch('sahara.service.api.v10.get_cluster')
    @mock.patch('sahara.plugins.base.PluginManager.get_plugin')
    def _assert_check_scaling(self,
                              get_plugin_p=None,
                              get_cluster_p=None,
                              data=None, cluster=None,
                              expected_message=None,
                              expected_exception=ex.InvalidReferenceException):

        get_cluster_p.return_value = cluster
        get_plugin_p.side_effect = _get_plugin

        with testtools.ExpectedException(expected_exception):
            try:
                c_s.check_cluster_scaling(data, cluster.id)
            except expected_exception as e:
                message = six.text_type(e).split('\n')[0]
                self.assertEqual(expected_message, message)
                raise e

    @mock.patch('sahara.service.api.v10.get_node_group_template')
    @mock.patch('sahara.utils.openstack.nova.client')
    @mock.patch("sahara.service.api.OPS")
    def test_check_cluster_scaling_resize_ng(self, ops, nova_client, get_ngt):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        ng1 = tu.make_ng_dict('ng', '42', ['namenode'], 1,
                              node_group_template_id='aaa')
        ng2 = tu.make_ng_dict('ng', '42', ['namenode'], 1,
                              resource=True)
        cluster = tu.create_cluster("cluster1", "tenant1", "fake", "0.1",
                                    [ng1],
                                    status=c_u.CLUSTER_STATUS_VALIDATING,
                                    id='12321')

        self._assert_check_scaling(
            data={}, cluster=cluster,
            expected_message="Cluster cannot be scaled "
                             "not in '" + c_u.CLUSTER_STATUS_ACTIVE +
            "' status. Cluster status: " +
            c_u.CLUSTER_STATUS_VALIDATING)

        cluster = tu.create_cluster("cluster1", "tenant1", "fake", "0.1",
                                    [ng1], status=c_u.CLUSTER_STATUS_ACTIVE,
                                    id='12321')
        data = {
            'resize_node_groups': [
                {
                    'name': 'a',
                    'count': 2
                }
            ],
        }
        self._assert_check_scaling(
            data=data, cluster=cluster,
            expected_message="Cluster doesn't contain "
                             "node group with name 'a'")
        data.update({'resize_node_groups': [
            {
                'name': 'a',
                'count': 2
            },
            {
                'name': 'a',
                'count': 2
            }
        ]})
        self._assert_check_scaling(
            data=data, cluster=cluster,
            expected_message=self.duplicates_detected,
            expected_exception=ex.InvalidDataException)

        data = {
            'resize_node_groups': [
                {
                    'name': 'ng',
                    'count': 2
                }
            ],
        }

        client = mock.Mock()
        nova_client.return_value = client
        client.flavors.list.return_value = []
        get_ngt.return_value = ng2

        self._assert_check_scaling(
            data=data, cluster=cluster,
            expected_message="Requested flavor '42' not found",
            expected_exception=ex.NotFoundException)

    @mock.patch("sahara.service.api.OPS")
    def test_check_cluster_scaling_add_ng(self, ops):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        ng1 = tu.make_ng_dict('ng', '42', ['namenode'], 1)
        cluster = tu.create_cluster("test-cluster", "tenant1", "fake",
                                    "0.1",
                                    [ng1], status=c_u.CLUSTER_STATUS_ACTIVE,
                                    id='12321')
        data = {
            'add_node_groups': [
                {
                    'name': 'a',
                    'flavor_id': '42',
                    'node_processes': ['namenode']
                },
                {
                    'name': 'a',
                    'flavor_id': '42',
                    'node_processes': ['namenode']
                }
            ]
        }
        self._assert_check_scaling(
            data=data, cluster=cluster,
            expected_message=self.duplicates_detected,
            expected_exception=ex.InvalidDataException)
        data = {
            'add_node_groups': [
                {
                    'name': 'ng',
                    'flavor_id': '42',
                    'node_processes': ['namenode']
                },
            ]
        }
        self._assert_check_scaling(
            data=data, cluster=cluster,
            expected_message="Can't add new nodegroup. "
                             "Cluster already has nodegroup "
                             "with name 'ng'")

        data = {
            'add_node_groups': [
                {
                    'name': 'very-very-very-very-very-very-long-ng-name',
                    'flavor_id': '42',
                    'node_processes': ['namenode'],
                    'count': 10
                },
            ]
        }
        patchers = u.start_patch()
        self._assert_check_scaling(
            data=data, cluster=cluster,
            expected_message="Composite hostname test-cluster-very-"
                             "very-very-very-very-very-long-ng-name-"
                             "010.novalocal in provisioned cluster exceeds "
                             "maximum limit 64 characters",
            expected_exception=ex.InvalidDataException)
        u.stop_patch(patchers)

    @mock.patch("sahara.utils.api.request_data")
    @mock.patch("sahara.utils.api.bad_request")
    def _assert_cluster_scaling_validation(self,
                                           bad_req=None,
                                           req_data=None,
                                           data=None,
                                           bad_req_i=None):
        m_func = mock.Mock()
        m_func.__name__ = "m_func"
        req_data.return_value = data
        v.validate(c_schema.CLUSTER_SCALING_SCHEMA,
                   self._create_object_fun)(m_func)(data=data,
                                                    cluster_id='42')

        self.assertEqual(1, req_data.call_count)
        self._assert_calls(bad_req, bad_req_i)

    @mock.patch("sahara.utils.api.request_data")
    @mock.patch("sahara.utils.api.bad_request")
    def _assert_cluster_scaling_validation_v2(self,
                                              bad_req=None,
                                              req_data=None,
                                              data=None,
                                              bad_req_i=None):
        m_func = mock.Mock()
        m_func.__name__ = "m_func"
        req_data.return_value = data
        v.validate(c_schema.CLUSTER_SCALING_SCHEMA_V2,
                   self._create_object_fun)(m_func)(data=data,
                                                    cluster_id='42')

        self.assertEqual(1, req_data.call_count)
        self._assert_calls(bad_req, bad_req_i)

    @mock.patch("sahara.service.api.OPS")
    def test_cluster_scaling_scheme_v_resize_ng(self, ops):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        self._create_object_fun = mock.Mock()
        data = {
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       '{} is not valid under any of the given schemas')
        )
        data = {
            'resize_node_groups': [{}]
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "resize_node_groups[0]: 'name' is a required property")
        )
        data = {
            'resize_node_groups': [
                {
                    'name': 'a'
                }
            ]
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "resize_node_groups[0]: 'count' is a required "
                       "property")
        )
        data = {
            'resize_node_groups': [
                {
                    'name': 'a',
                    'flavor_id': '42',
                    'count': 2
                }
            ]
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "resize_node_groups[0]: Additional properties are not "
                       "allowed ('flavor_id' was unexpected)")
        )

    @mock.patch("sahara.service.api.OPS")
    def test_cluster_scaling_scheme_v_resize_ng_v2(self, ops):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        self._create_object_fun = mock.Mock()
        data = {
        }
        self._assert_cluster_scaling_validation_v2(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       '{} is not valid under any of the given schemas')
        )
        data = {
            'resize_node_groups': [{}]
        }
        self._assert_cluster_scaling_validation_v2(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "resize_node_groups[0]: 'name' is a required property")
        )
        data = {
            'resize_node_groups': [
                {
                    'name': 'a'
                }
            ]
        }
        self._assert_cluster_scaling_validation_v2(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "resize_node_groups[0]: 'count' is a required "
                       "property")
        )
        data = {
            'resize_node_groups': [
                {
                    'name': 'a',
                    'flavor_id': '42',
                    'instances': ['id1'],
                    'count': 2
                }
            ]
        }
        self._assert_cluster_scaling_validation_v2(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "resize_node_groups[0]: Additional properties are not "
                       "allowed ('flavor_id' was unexpected)")
        )

    @mock.patch("sahara.service.api.OPS")
    def test_cluster_scaling_validation_add_ng(self, ops):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        data = {
            'add_node_groups': [
                {
                    "node_group_template_id": "5185a809-6bf7-"
                                              "44ed-9de3-618270550e2c",
                }
            ]
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "add_node_groups[0]: {'node_group_template_id': "
                       "'5185a809-6bf7-44ed-9de3-618270550e2c'} "
                       "is not valid under any of the given schemas")
        )
        data = {
            'add_node_groups': [
                {
                    "node_group_template_id": "5185a809-6bf7-"
                                              "44ed-9de3-618270550e2c",
                    'name': 'a'
                }
            ]
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "add_node_groups[0]: {'node_group_template_id': "
                       "'5185a809-6bf7-44ed-9de3-618270550e2c', "
                       "'name': 'a'} is not valid under any "
                       "of the given schemas")
        )

    @mock.patch("sahara.service.api.OPS")
    def test_cluster_scaling_validation_right_schema(self, ops):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        data = {
            'add_node_groups': [
                {
                    "node_group_template_id": "5185a809-6bf7-"
                                              "44ed-9de3-618270550e2c",
                    'name': 'a',
                    'count': 3
                }
            ]
        }
        self._assert_cluster_scaling_validation(
            data=data
        )
        data = {
            'resize_node_groups': [
                {
                    'name': 'a',
                    'count': 3
                }
            ]
        }
        self._assert_cluster_scaling_validation(
            data=data
        )
        data = {
            'resize_node_groups': [
                {
                    'name': 'a',
                    'count': 3
                }
            ],
            'add_node_groups': [
                {
                    "node_group_template_id": "5185a809-6bf7-"
                                              "44ed-9de3-618270550e2c",
                    'name': 'a',
                    'count': 3
                }
            ]
        }
        self._assert_cluster_scaling_validation(
            data=data
        )

    @mock.patch("sahara.service.api.OPS")
    def test_cluster_scaling_scheme_validation_types(self, ops):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        data = {
            'resize_node_groups': {},
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "resize_node_groups: {} is not of type 'array'")
        )
        data = {
            'add_node_groups': {}
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "add_node_groups: {} is not of type 'array'")
        )
        data = {
            'resize_node_groups': [],
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       'resize_node_groups: [] is too short')
        )

    @mock.patch("sahara.service.api.OPS")
    def test_cluster_scaling_v_right_data(self, ops):
        self.setup_context(tenant_id='t')
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        self._create_object_fun = c_s.check_cluster_scaling

        data = {
            'resize_node_groups': [
                {
                    'name': 'ng',
                    'count': 4
                }
            ],
            'add_node_groups': [
                {
                    'name': 'a',
                    'flavor_id': '42',
                    'node_processes': ['namenode'],
                    'count': 3
                },
            ]
        }
        patchers = u.start_patch()
        self._assert_cluster_scaling_validation(data=data)
        u.stop_patch(patchers)

    @mock.patch("sahara.service.api.OPS")
    def test_check_cluster_scaling_wrong_engine(self, ops):
        ops.get_engine_type_and_version.return_value = "direct.1.1"
        ng1 = tu.make_ng_dict('ng', '42', ['namenode'], 1)
        cluster = tu.create_cluster(
            "cluster1", "tenant1", "fake", "0.1", [ng1],
            status=c_u.CLUSTER_STATUS_ACTIVE, id='12321',
            sahara_info={"infrastructure_engine": "heat.1.1"})

        self._assert_check_scaling(
            data={}, cluster=cluster,
            expected_message="Cluster created with heat.1.1 infrastructure "
                             "engine can't be scaled with direct.1.1 engine")

    @mock.patch("sahara.service.api.OPS")
    def test_check_heat_cluster_scaling_missing_engine(self, ops):
        ops.get_engine_type_and_version.return_value = "heat.1.1"
        ng1 = tu.make_ng_dict('ng', '42', ['namenode'], 1)
        cluster = tu.create_cluster("cluster1", "tenant1", "fake", "0.1",
                                    [ng1], status=c_u.CLUSTER_STATUS_ACTIVE,
                                    id='12321')

        self._assert_check_scaling(
            data={}, cluster=cluster,
            expected_message="Cluster created before Juno release can't be "
                             "scaled with heat.1.1 engine")

    @mock.patch('sahara.utils.openstack.images.image_manager')
    @mock.patch('sahara.utils.openstack.nova.client')
    @mock.patch("sahara.service.api.OPS")
    def test_check_cluster_scaling_missing_resource(self, ops,
                                                    m_nova, m_image):
        ops.get_engine_type_and_version.return_value = "heat.1.1"
        ng1 = tu.make_ng_dict('ng', '42', ['namenode'], 1)

        nova = mock.Mock()
        m_nova.return_value = nova
        nova.keypairs.get.side_effect = u._get_keypair
        cluster = tu.create_cluster(
            "cluster1", "tenant1", "fake", "0.1", [ng1],
            status=c_u.CLUSTER_STATUS_ACTIVE,
            sahara_info={"infrastructure_engine": "heat.1.1"},
            id='12321', user_keypair_id='keypair')
        self._assert_check_scaling(
            data={}, cluster=cluster,
            expected_exception=ex.NotFoundException,
            expected_message="Requested keypair 'keypair' not found")

        image = mock.Mock()
        m_image.return_value = image
        image.list_registered.return_value = [mock.Mock(id='image1'),
                                              mock.Mock(id='image2')]
        cluster = tu.create_cluster(
            "cluster1", "tenant1", "fake", "0.1", [ng1],
            status=c_u.CLUSTER_STATUS_ACTIVE,
            sahara_info={"infrastructure_engine": "heat.1.1"},
            id='12321', default_image_id='image_id',
            user_keypair_id='test_keypair')
        self._assert_check_scaling(
            data={}, cluster=cluster,
            expected_message="Requested image 'image_id' is not registered")
