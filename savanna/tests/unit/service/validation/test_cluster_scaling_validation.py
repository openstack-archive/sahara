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
import unittest2

import savanna.db.models as m
from savanna import exceptions as ex
from savanna.plugins.vanilla import plugin
from savanna.service import api
import savanna.service.validation as v
from savanna.service.validations import clusters_scaling as c_s
from savanna.tests.unit.service.validation import utils as u


def _get_plugin(plugin_name):
    if plugin_name == 'vanilla':
        return plugin.VanillaProvider()
    return None


class TestScalingValidation(unittest2.TestCase):
    def setUp(self):
        api.plugin_base.setup_plugins()
        self._create_object_fun = mock.Mock()

    @mock.patch('savanna.service.api.get_cluster')
    @mock.patch('savanna.plugins.base.PluginManager.get_plugin')
    def _assert_check_scaling(self,
                              get_plugin_p=None,
                              get_cluster_p=None,
                              data=None, cluster=None,
                              expected_message=None):

        get_cluster_p.return_value = cluster
        get_plugin_p.side_effect = _get_plugin

        with self.assertRaises(ex.InvalidException):
            try:
                c_s.check_cluster_scaling(data, cluster.id)
            except ex.InvalidException as e:
                self.assertEqual(expected_message, e.message)
                raise e

    def test_check_cluster_scaling_resize_ng(self):
        cluster = m.Cluster('test-cluster', 'tenant', 'vanilla', '1.2.2')
        cluster.status = 'Validating'
        ng = m.NodeGroup('ng', '42', ['namenode'], 1)
        cluster.node_groups.append(ng)
        self._assert_check_scaling(data={}, cluster=cluster,
                                   expected_message=
                                   "Cluster cannot be scaled "
                                   "not in 'Active' "
                                   "status. Cluster status: "
                                   "Validating")
        cluster.status = 'Active'
        data = {
            'resize_node_groups': [
                {
                    'name': 'a',
                    'flavor_id': '42',
                    'node_processes': ['namenode']
                }
            ],
        }
        self._assert_check_scaling(data=data, cluster=cluster,
                                   expected_message=
                                   "Cluster doesn't contain "
                                   "node group with name 'a'")
        data.update({'resize_node_groups': [
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
        ]})
        self._assert_check_scaling(data=data, cluster=cluster,
                                   expected_message=
                                   'Duplicates in node '
                                   'group names are detected')

    def test_check_cluster_scaling_add_ng(self):
        cluster = m.Cluster('test-cluster', 'tenant', 'vanilla', '1.2.2')
        ng = m.NodeGroup('ng', '42', ['namenode'], 1)
        cluster.node_groups.append(ng)
        cluster.status = 'Active'
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
        self._assert_check_scaling(data=data, cluster=cluster,
                                   expected_message=
                                   'Duplicates in node '
                                   'group names are detected')
        data = {
            'add_node_groups': [
                {
                    'name': 'ng',
                    'flavor_id': '42',
                    'node_processes': ['namenode']
                },
            ]
        }
        self._assert_check_scaling(data=data, cluster=cluster,
                                   expected_message=
                                   "Can't add new nodegroup. "
                                   "Cluster already has nodegroup "
                                   "with name 'ng'")

    def _assert_calls(self, mock, call_info):
        if not call_info:
            self.assertEqual(mock.call_count, 0)
        else:
            self.assertEqual(mock.call_count, call_info[0])
            self.assertEqual(mock.call_args[0][0].code, call_info[1])
            self.assertEqual(mock.call_args[0][0].message, call_info[2])

    @mock.patch("savanna.utils.api.request_data")
    @mock.patch("savanna.utils.api.bad_request")
    def _assert_cluster_scaling_validation(self,
                                           bad_req=None,
                                           req_data=None,
                                           data=None,
                                           bad_req_i=None):
        m_func = mock.Mock()
        m_func.__name__ = "m_func"
        req_data.return_value = data
        v.validate(c_s.CLUSTER_SCALING_SCHEMA,
                   self._create_object_fun)(m_func)(data=data,
                                                    cluster_id='42')

        self.assertEqual(req_data.call_count, 1)
        self._assert_calls(bad_req, bad_req_i)

    def test_cluster_scaling_scheme_v_resize_ng(self):
        self._create_object_fun = mock.Mock()
        data = {
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'{} is not valid under any of the given schemas')
        )
        data = {
            'resize_node_groups': [{}]
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u"'name' is a required property")
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
                       u"'count' is a required property")
        )

    def test_cluster_scaling_validation_add_ng(self):
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
                       "{'node_group_template_id': "
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
                       u"{'node_group_template_id': "
                       u"'5185a809-6bf7-44ed-9de3-618270550e2c', "
                       u"'name': 'a'} is not valid under any "
                       u"of the given schemas")
        )

    def test_cluster_scaling_validation_right_schema(self):
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

    def test_cluster_scaling_scheme_validation_types(self):
        data = {
            'resize_node_groups': {},
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u"{} is not of type 'array'")
        )
        data = {
            'add_node_groups': {}
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u"{} is not of type 'array'")
        )
        data = {
            'resize_node_groups': [],
        }
        self._assert_cluster_scaling_validation(
            data=data,
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'[] is too short')
        )

    def test_cluster_scaling_v_right_data(self):
        self._create_object_fun = c_s.check_cluster_scaling
        cluster = m.Cluster('test-cluster', 'tenant', 'vanilla', '1.2.2')
        ng = m.NodeGroup('ng', '42', ['namenode'], 1)
        cluster.node_groups.append(ng)
        cluster.status = 'Active'

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
