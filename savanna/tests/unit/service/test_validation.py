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
import novaclient.exceptions as nova_ex
from oslo.config import cfg
import unittest2

from savanna.plugins.vanilla import plugin
from savanna.service import api
import savanna.service.validation as v
from savanna.service.validations import cluster_templates as ct
from savanna.service.validations import clusters as c
from savanna.service.validations import node_group_templates as nt
from savanna.utils import resources

CONF = cfg.CONF
CONF.import_opt('plugins', 'savanna.config')

_types_checks = {
    "string": [1, (), {}],
    "integer": ["a", (), {}],
    "uuid": ["z550e8400-e29b-41d4-a716-446655440000", 1, "a", (), {}],
    "array": [{}, 'a', 1]
}


def _update_data(data, update):
    data.update(update)
    return data


class TestValidation(unittest2.TestCase):
    def setUp(self):
        self._create_object_fun = None
        api.plugin_base.setup_plugins()

    def tearDown(self):
        self._create_object_fun = None

    def _assert_calls(self, mock, call_info):
        if not call_info:
            self.assertEqual(mock.call_count, 0)
        else:
            self.assertEqual(mock.call_count, call_info[0])
            self.assertEqual(mock.call_args[0][0].code, call_info[1])
            self.assertEqual(mock.call_args[0][0].message, call_info[2])

    def start_patch(self, data):
        request_data_p = mock.patch("savanna.utils.api.request_data")
        bad_req_p = mock.patch("savanna.utils.api.bad_request")
        not_found_p = mock.patch("savanna.utils.api.not_found")
        int_err_p = mock.patch("savanna.utils.api.internal_error")
        get_clusters_p = mock.patch("savanna.service.api.get_clusters")
        get_ng_templates_p = \
            mock.patch("savanna.service.api.get_node_group_templates")
        get_ng_template_p = \
            mock.patch("savanna.service.api.get_node_group_template")
        get_plugins_p = mock.patch("savanna.service.api.get_plugins")
        get_plugin_p = \
            mock.patch("savanna.plugins.base.PluginManager.get_plugin")
        get_image_p = mock.patch("savanna.service.api.get_image")
        get_cl_templates_p = \
            mock.patch("savanna.service.api.get_cluster_templates")
        get_cl_template_p = \
            mock.patch("savanna.service.api.get_cluster_template")
        nova_p = mock.patch("savanna.utils.openstack.nova.client")

        request_data = request_data_p.start()
        bad_req = bad_req_p.start()
        not_found = not_found_p.start()
        int_err = int_err_p.start()
        get_clusters = get_clusters_p.start()
        get_ng_templates = get_ng_templates_p.start()
        get_ng_template = get_ng_template_p.start()
        get_plugins = get_plugins_p.start()
        get_plugin = get_plugin_p.start()
        get_cl_templates = get_cl_templates_p.start()
        get_cl_template_p.start()
        get_image = get_image_p.start()
        nova = nova_p.start()
        get_cl_templates.return_value = []

        def _get_keypair(name):
            if name is not "test_keypair":
                raise nova_ex.NotFound("")

        def _get_flavor(flavor_id):
            if flavor_id is not "42":
                raise nova_ex.NotFound("")

        nova().flavors.get.side_effect = _get_flavor
        nova().keypairs.get.side_effect = _get_keypair

        # stub clusters list
        get_clusters.return_value = getattr(self, "_clusters_data", [
            resources.Resource("cluster", {
                "name": "test"
            })
        ])
        # stub node templates
        get_ng_templates.return_value = getattr(self, "_templates_data", [
            resources.Resource("node_template", {
                "name": "test"
            })
        ])

        get_cl_templates.return_value = getattr(self, "_templates_data", [
            resources.Resource("cluster_template", {
                "name": "test",
            })
        ])

        vanilla = plugin.VanillaProvider()
        vanilla.name = 'vanilla'
        get_plugins.return_value = [vanilla]

        def _get_ng_template(name):
            for template in get_ng_templates():
                if template.name == name:
                    return template
            return None

        def _get_plugin(name):
            if name == 'vanilla':
                return vanilla
            return None

        def _get_image(id=None):
            if id is not '550e8400-e29b-41d4-a716-446655440000':
                raise nova_ex.NotFound("")

        get_plugin.side_effect = _get_plugin
        get_ng_template.side_effect = _get_ng_template
        get_image.side_effect = _get_image
        # request data to validate
        request_data.return_value = data
        patchers = (request_data_p, bad_req_p, not_found_p, int_err_p,
                    get_clusters_p, get_ng_templates_p, get_ng_template_p,
                    get_plugins_p, get_plugin_p, get_image_p,
                    get_cl_template_p, get_cl_templates_p, nova_p)
        return bad_req, int_err, not_found, request_data, patchers

    def stop_patch(self, patchers):
        for patcher in patchers:
            patcher.stop()

    def _assert_create_object_validation(
            self, scheme, data, bad_req_i=None,
            not_found_i=None, int_err_i=None):

        bad_req, int_err, not_found, request_data, patchers = \
            self.start_patch(data)
        # mock function that should be validated
        m_func = mock.Mock()
        m_func.__name__ = "m_func"
        v.validate(scheme, self._create_object_fun)(m_func)(data=data)

        self.assertEqual(request_data.call_count, 1)
        self._assert_calls(bad_req, bad_req_i)
        self._assert_calls(not_found, not_found_i)
        self._assert_calls(int_err, int_err_i)
        self.stop_patch(patchers)

    def _assert_object_name_validation(self, scheme, data, name_type):

        data.update({'name': None})
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"None is not of type 'string'")
        )
        data.update({'name': ""})
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'' is too short")
        )
        data.update({'name': ('a' * 51)})
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'%s' is too long" % ('a' * 51))
        )
        data.update({'name': 'a-!'})
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'a-!' is not a '%s'" % name_type)
        )
        data.update({'name': 'aa_'})
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'aa_' is not a '%s'" % name_type)
        )
        # For cluster templates validating
        if name_type == 'valid_name':
            data.update({'name': '1-a'})
            self._assert_create_object_validation(
                scheme,
                data,
                bad_req_i=(1, "VALIDATION_ERROR",
                           u"'1-a' is not a '%s'" % name_type)
            )
            data.update({'name': 'aca'})
            self._assert_create_object_validation(
                scheme,
                data
            )

    def test_cluster_create_v_required(self):
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'test-name'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'plugin_name' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'testname',
                'plugin_name': 'vanilla'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'hadoop_version' is a required property")
        )

        self._assert_create_object_validation(
            scheme,
            {
                'name': 'testname',
                'plugin_name': 'vanilla',
                'hadoop_version': '1'
            },
            bad_req_i=(1, "INVALID_REFERENCE",
                       "Requested plugin 'vanilla' "
                       "doesn't support version '1'"),
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'testname',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2'
            },
        )

    def test_cluster_create_v_types(self):
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        data = {
            'name': "testname",
            'plugin_name': "vanilla",
            'hadoop_version': "1.1.2"
        }
        self._assert_types(data, scheme)

    def test_cluster_create_v_name_base(self):
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        data = {
            'name': "testname",
            'plugin_name': "vanilla",
            'hadoop_version': "1.1.2"
        }
        self._assert_object_name_validation(scheme, data, 'hostname')

    def test_cluster_template_create_v_types(self):
        self._create_object_fun = c.check_cluster_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA
        data = {
            'name': "testname",
            'plugin_name': "vanilla",
            'hadoop_version': "1.1.2"
        }
        self._assert_types(data, scheme)

    def test_cluster_create_template_v_required(self):
        self._create_object_fun = ct.check_cluster_template_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA

        self._assert_create_object_validation(
            scheme,
            {},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'test-name'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'plugin_name' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'testname',
                'plugin_name': 'vanilla'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'hadoop_version' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'testname',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2'
            })

    def test_cluster_template_create_v_name_base(self):
        self._create_object_fun = ct.check_cluster_template_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA
        data = {
            'name': "testname",
            'plugin_name': "vanilla",
            'hadoop_version': "1.1.2"
        }
        self._assert_object_name_validation(scheme, data, 'valid_name')

    def test_node_groups_create_required(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'a'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'flavor_id' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'hadoop_version' is a required property")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'node_processes' is a required property")
        )

    def test_ng_template_create_v_names(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        data = {
            'name': 'a',
            'flavor_id': '42',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.1.2',
            'node_processes': ['namenode']
        }
        self._assert_object_name_validation(scheme, data, "valid_name")

    def test_ng_template_create_v_node_processes(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': "a",
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': []
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'[] is too short')
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "a",
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': ["namenode", "namenode"]
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       'Duplicates in node processes have been detected')
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': ['wrong_process']
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin supports the following node procesess: "
                       "['namenode', 'datanode', 'secondarynamenode', "
                       "'tasktracker', 'jobtracker']")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': ['namenode',
                                   'datanode',
                                   'secondarynamenode',
                                   'tasktracker',
                                   'jobtracker']
            }
        )

    def test_ng_template_create_v_minimum_ints(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': ['wrong_process'],
                'volumes_per_node': -1
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'-1.0 is less than the minimum of 0')
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'a',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': ['wrong_process'],
                'volumes_size': 0
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       u'0.0 is less than the minimum of 1')
        )

    def _assert_types(self, default_data, scheme):
        for p_name in scheme['properties']:
            prop = scheme['properties'][p_name]
            if prop["type"] in _types_checks:
                for type_ex in _types_checks[prop["type"]]:
                    data = default_data.copy()
                    value = type_ex
                    value_str = str(value)
                    if isinstance(value, str):
                        value_str = "'%s'" % value_str
                    data.update({p_name: value})
                    self._assert_create_object_validation(
                        scheme,
                        data,
                        bad_req_i=(1, 'VALIDATION_ERROR',
                                   u"%s is not of type '%s'"
                                   % (value_str, prop["type"]))
                    )

    def test_ng_template_create_v_types(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        default_data = {
            'name': 'a', 'flavor_id': '42',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.1.2',
            'node_processes': ['namenode']
        }
        self._assert_types(default_data, scheme)

    def test_ng_template_create_v_unique_ng(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        data = {
            'name': 'test',
            'flavor_id': '42',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.1.2',
            'node_processes': ['namenode']}
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, 'NAME_ALREADY_EXISTS',
                       "NodeGroup template with name 'test' already exists")
        )

    def test_cluster_create_v_unique_cl(self):
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        data = {
            'name': 'test',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.1.2'
        }
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, 'NAME_ALREADY_EXISTS',
                       "Cluster with name 'test' already exists")
        )

    def test_cluster_template_create_v_unique_cl(self):
        self._create_object_fun = ct.check_cluster_template_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA
        data = {
            'name': 'test',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.1.2'
        }
        self._assert_create_object_validation(
            scheme,
            data,
            bad_req_i=(1, 'NAME_ALREADY_EXISTS',
                       "Cluster template with name 'test' already exists")
        )

    def test_ng_template_create_v_ng_configs(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'test-ng',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': ['namenode'],
                'node_configs': {
                    'HDFS': {
                        u'hadoop.tmp.dir': '/temp/'
                    }
                }}
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'test-ng',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
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
            scheme,
            {
                'name': 'test-ng',
                'flavor_id': '42',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
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

    def test_cluster_create_v_keypair_id(self):
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'user_keypair_id': '1'
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "'1' is not a 'valid_name'")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'user_keypair_id': '!'},
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "'!' is not a 'valid_name'")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "testname",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'user_keypair_id': 'wrong_keypair'
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Requested keypair 'wrong_keypair' not found")
        )

    def test_cluster_create_v_image_exists(self):
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
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
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "wrong_plugin",
                'hadoop_version': "1.1.2",
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Savanna doesn't contain plugin "
                       "with name 'wrong_plugin'")
        )

    def test_cluster_template_create_v_plugin_name_exists(self):
        self._create_object_fun = ct.check_cluster_template_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "wrong_plugin",
                'hadoop_version': "1.1.2",
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Savanna doesn't contain plugin "
                       "with name 'wrong_plugin'")
        )

    def test_ng_template_create_v_flavor_exists(self):
        self._create_object_fun = nt.check_node_group_template_create
        scheme = nt.NODE_GROUP_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': 'test-ng',
                'flavor_id': '1',
                'plugin_name': 'vanilla',
                'hadoop_version': '1.1.2',
                'node_processes': ['namenode']
            },
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Requested flavor '1' not found")
        )

    def _assert_cluster_configs_validation(self, scheme):
        data = {
            'name': 'test-cluster',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.1.2',
            'cluster_configs': {
                'HDFS': {
                    u'hadoop.tmp.dir': '/temp/'
                }
            }
        }
        self._assert_create_object_validation(
            scheme,
            data
        )
        self._assert_create_object_validation(
            scheme,
            _update_data(data, {
                'cluster_configs': {
                    'wrong_target': {
                        u'hadoop.tmp.dir': '/temp/'
                    }
                }}),
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin doesn't contain applicable "
                       "target 'wrong_target'")
        )
        self._assert_create_object_validation(
            scheme,
            _update_data(data, {
                'cluster_configs': {
                    'HDFS': {
                        u's': '/temp/'
                    }
                }
            }),
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin's applicable target 'HDFS' doesn't "
                       "contain config with name 's'")
        )

    def test_cluster_create_v_cluster_configs(self):
        self._create_object_fun = c.check_cluster_create
        scheme = c.CLUSTER_SCHEMA
        self._assert_cluster_configs_validation(scheme)

    def test_cluster_create_template_v_cluster_configs(self):
        self._create_object_fun = ct.check_cluster_template_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA
        self._assert_cluster_configs_validation(scheme)

    def test_cluster_create_template_v_ng(self):
        self._create_object_fun = ct.check_cluster_template_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'node_groups': [
                    {'name': 'a',
                     'flavor_id': '42',
                     'node_processes': ['namenode'],
                     'count': 3}
                ]
            },
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'node_groups': [
                    {'name': 'a'}
                ]
            },
            bad_req_i=(1, 'VALIDATION_ERROR',
                       "{'name': 'a'} is not valid under "
                       "any of the given schemas")
        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'node_groups': [
                    {'name': 'a',
                     'flavor_id': '42'}
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "{'name': 'a', 'flavor_id': '42'} "
                       "is not valid under any of the given schemas")

        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'node_groups': [
                    {'name': 'a',
                     'flavor_id': '42',
                     'node_processes': ['namenode']}
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "{'node_processes': ['namenode'], "
                       "'name': 'a', "
                       "'flavor_id': '42'} "
                       "is not valid under any of the given schemas")
        )

    def test_cluster_create_template_v_ng_templates(self):
        self._create_object_fun = ct.check_cluster_template_create
        scheme = ct.CLUSTER_TEMPLATE_SCHEMA
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'node_groups': [
                    {
                        "node_group_template_id": "",
                        "name": "test",
                    }
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "{'node_group_template_id': '', 'name': 'test'} "
                       "is not valid under any of the given schemas")

        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'node_groups': [
                    {
                        "node_group_template_id": "test",
                        "name": "test",
                        'count': 3
                    }
                ]
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "{'count': 3, "
                       "'node_group_template_id': 'test', "
                       "'name': 'test'} "
                       "is not valid under any of the given schemas")

        )
        self._assert_create_object_validation(
            scheme,
            {
                'name': "test-name",
                'plugin_name': "vanilla",
                'hadoop_version': "1.1.2",
                'node_groups': [
                    {
                        "node_group_template_id": "550e8400-e29b-41d4-a716-"
                                                  "446655440000",
                        "name": "test",
                        'count': 3
                    }
                ]
            },

        )
