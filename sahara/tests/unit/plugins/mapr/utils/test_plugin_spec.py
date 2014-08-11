# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.


import os

import sahara.plugins.mapr.util.plugin_spec as ps
import sahara.plugins.provisioning as p
import sahara.tests.unit.base as b

import mock as m


class PluginSpecTest(b.SaharaTestCase):

    def assertItemsEqual(self, expected, actual):
        for e in expected:
            self.assertIn(e, actual)
        for a in actual:
            self.assertIn(a, expected)

    def assertDictValueItemsEqual(self, expected, actual):
        self.assertItemsEqual(expected.keys(), actual.keys())
        for k in actual:
            self.assertItemsEqual(expected[k], actual[k])

    @m.patch.object(ps.PluginSpec, '__init__', new=lambda i: None)
    def setUp(self):
        super(PluginSpecTest, self).setUp()
        path = 'tests/unit/plugins/mapr/utils/resources/plugin_spec.json'
        plugin_spec = ps.PluginSpec()
        plugin_spec.base_dir = os.path.dirname(path)
        plugin_spec.plugin_spec_dict = plugin_spec._load_plugin_spec_dict(path)
        self.plugin_spec = plugin_spec

    def test_load_service_file_name_map(self):
        plugin_spec = self.plugin_spec

        actual = plugin_spec._load_service_file_name_map()
        expected = {'service_2': ['file_0', 'file_1', 'file_2'],
                    'general': ['file_3', None]}
        self.assertDictValueItemsEqual(expected, actual)

    def test_load_file_name_config_map(self):
        plugin_spec = self.plugin_spec

        actual = plugin_spec._load_file_name_config_map()
        expected = {'file_1': ['k1', 'k0', 'k3', 'k2'], None: ['k4']}
        self.assertDictValueItemsEqual(expected, actual)

    def test_load_default_configs(self):
        pls = self.plugin_spec
        pls.service_file_name_map = pls._load_service_file_name_map()

        actual = pls._load_default_configs()
        expected = {'service_2': {'file_1': {'k0': 'v0', 'k1': 'v1'},
                                  'file_2': {'k0': 'v0', 'k1': 'v1'}},
                    'general': {'file_3': {'content': 'Some unparsable data'}}}
        self.assertEqual(expected, actual)

    def test_load_service_node_process_map(self):
        pls = self.plugin_spec

        actual = pls._load_service_node_process_map()
        expected = {'service_2': ['node_process_0', 'node_process_1']}
        self.assertDictValueItemsEqual(expected, actual)

    def test_load_plugin_config_items(self):
        pls = self.plugin_spec
        pls.service_file_name_map = pls._load_service_file_name_map()
        pls.default_configs = pls._load_default_configs()
        pls.plugin_config_objects = pls._load_plugin_config_objects()
        pls.file_name_config_map = pls._load_file_name_config_map()

        actual = pls._load_plugin_config_items()
        expected = [{'default_value': 3, 'name': 'k1', 'config_values': None,
                     'priority': 1, 'config_type': 'int', 'file': 'file_1',
                     'applicable_target': 'service_2', 'is_optional': False,
                     'scope': 'node', 'description': None},
                    {'default_value': None, 'name': 'k2',
                     'config_values': None, 'priority': 2,
                     'config_type': 'bool', 'file': 'file_1',
                     'applicable_target': 'service_2', 'is_optional': True,
                     'scope': 'cluster', 'description': None},
                    {'default_value': 'default_value_0', 'name': 'k0',
                     'config_values': None, 'priority': 2, 'file': 'file_1',
                     'config_type': 'string', 'applicable_target': 'service_2',
                     'is_optional': False, 'scope': 'cluster',
                     'description': 'description_0'},
                    {'default_value': None, 'name': 'k3',
                     'config_values': None, 'priority': 2,
                     'config_type': 'string', 'file': 'file_1',
                     'applicable_target': 'service_2', 'is_optional': True,
                     'scope': 'node', 'description': None},
                    {'default_value': None, 'name': 'k4',
                     'config_values': None, 'priority': 2,
                     'config_type': 'string', 'file': None,
                     'applicable_target': 'general', 'is_optional': False,
                     'scope': 'cluster', 'description': None}]
        self.assertItemsEqual(expected, actual)

    def test_load_plugin_configs(self):
        pls = self.plugin_spec
        pls.service_file_name_map = pls._load_service_file_name_map()
        pls.plugin_config_objects = pls._load_plugin_config_objects()
        pls.file_name_config_map = pls._load_file_name_config_map()
        pls.plugin_config_items = pls._load_plugin_config_items()

        actual = pls._load_plugin_configs()
        expected = {'service_2': {'file_1': {'k0': 'default_value_0', 'k1': 3,
                                             'k2': None, 'k3': None}},
                    'general': {None: {'k4': None}}}
        self.assertEqual(expected, actual)

    def test_load_default_plugin_configs(self):
        pls = self.plugin_spec
        pls.service_file_name_map = pls._load_service_file_name_map()
        pls.default_configs = pls._load_default_configs()
        pls.plugin_config_objects = pls._load_plugin_config_objects()
        pls.file_name_config_map = pls._load_file_name_config_map()
        pls.plugin_config_items = pls._load_plugin_config_items()
        pls.plugin_configs = pls._load_plugin_configs()

        actual = pls._load_default_plugin_configs()
        expected = {'service_2': {'file_1': {'k0': 'default_value_0', 'k1': 3,
                                             'k2': None, 'k3': None},
                                  'file_2': {'k0': 'v0', 'k1': 'v1'}},
                    'general': {None: {'k4': None},
                                'file_3': {'content': 'Some unparsable data'}}}
        self.assertEqual(expected, actual)

    def test_load_plugin_config_objects(self):
        pls = self.plugin_spec
        pls.service_file_name_map = pls._load_service_file_name_map()
        pls.default_configs = pls._load_default_configs()

        actual = pls._load_plugin_config_objects()
        expected = [p.Config('k0', 'service_2', 'cluster',
                             default_value='default_value_0',
                             description='description_0'),
                    p.Config('k1', 'service_2', 'node',
                             config_type='int', default_value=3, priority=1),
                    p.Config('k2', 'service_2', 'cluster',
                             config_type='bool', is_optional=True),
                    p.Config('k3', 'service_2', 'node', is_optional=True),
                    p.Config('k4', 'general', 'cluster', is_optional=False)]
        m_actual = map(lambda i: i.to_dict(), actual)
        m_expected = map(lambda i: i.to_dict(), expected)
        self.assertItemsEqual(m_expected, m_actual)

    def test_get_node_process_service(self):
        pls = self.plugin_spec
        pls.service_node_process_map = pls._load_service_node_process_map()

        actual = pls.get_node_process_service('node_process_0')
        expected = 'service_2'
        self.assertEqual(expected, actual)

    def test_get_default_plugin_configs(self):
        pls = self.plugin_spec
        pls.service_file_name_map = pls._load_service_file_name_map()
        pls.default_configs = pls._load_default_configs()
        pls.plugin_config_objects = pls._load_plugin_config_objects()
        pls.file_name_config_map = pls._load_file_name_config_map()
        pls.plugin_config_items = pls._load_plugin_config_items()
        pls.plugin_configs = pls._load_plugin_configs()
        pls.default_plugin_configs = pls._load_default_plugin_configs()

        actual = pls.get_default_plugin_configs(['service_2'])
        expected = {'service_2': {'file_1': {'k0': 'default_value_0', 'k1': 3,
                                             'k2': None, 'k3': None},
                                  'file_2': {'k0': 'v0', 'k1': 'v1'}}}
        self.assertEqual(expected, actual)

    def test_get_config_file(self):
        path = 'tests/unit/plugins/mapr/utils/resources/plugin_spec.json'
        plugin_spec = ps.PluginSpec(path)

        arg = {'service': 'service_2', 'scope': 'node', 'name': 'k1'}
        actual = plugin_spec.get_config_file(**arg)
        expected = 'file_1'
        self.assertEqual(expected, actual)

        arg = {'service': 'service_1', 'scope': 'node', 'name': 'k1'}
        actual = plugin_spec.get_config_file(**arg)
        expected = None
        self.assertEqual(expected, actual)

    def test_get_version_config_objects(self):
        actual = self.plugin_spec.get_version_config_objects()
        expected = [p.Config(name='service_2 Version',
                             applicable_target='service_2',
                             scope='cluster',
                             config_type='dropdown',
                             config_values=[('v1', 'v1'), ('v2', 'v2')],
                             is_optional=False,
                             priority=1)]
        m_actual = map(lambda i: i.to_dict(), actual)
        m_expected = map(lambda i: i.to_dict(), expected)
        self.assertItemsEqual(m_expected, m_actual)

    def test_get_configs(self):
        pls = self.plugin_spec
        pls.service_file_name_map = pls._load_service_file_name_map()
        pls.default_configs = pls._load_default_configs()
        pls.plugin_config_objects = pls._load_plugin_config_objects()

        actual = pls.get_configs()
        expected = [p.Config('k0', 'service_2', 'cluster',
                             default_value='default_value_0',
                             description='description_0'),
                    p.Config('k1', 'service_2', 'node',
                             config_type='int', default_value=3, priority=1),
                    p.Config('k2', 'service_2', 'cluster',
                             config_type='bool', is_optional=True),
                    p.Config('k3', 'service_2', 'node', is_optional=True),
                    p.Config('k4', 'general', 'cluster', is_optional=False),
                    p.Config('service_2 Version', 'service_2', 'cluster',
                             config_type='dropdown',
                             config_values=[('v1', 'v1'), ('v2', 'v2')],
                             is_optional=False, priority=1)]
        m_actual = map(lambda i: i.to_dict(), actual)
        m_expected = map(lambda i: i.to_dict(), expected)
        self.assertItemsEqual(m_expected, m_actual)

    def test_init(self):
        path = 'tests/unit/plugins/mapr/utils/resources/plugin_spec.json'
        plugin_spec = ps.PluginSpec(path)

        actual = plugin_spec.service_file_name_map
        expected = {'service_2': ['file_0', 'file_1', 'file_2'],
                    'general': [None, 'file_3']}
        self.assertDictValueItemsEqual(expected, actual)

        actual = plugin_spec.file_name_config_map
        expected = {'file_1': ['k1', 'k0', 'k3', 'k2'], None: ['k4']}
        self.assertDictValueItemsEqual(expected, actual)

        actual = plugin_spec.default_configs
        expected = {'service_2': {'file_1': {'k0': 'v0', 'k1': 'v1'},
                                  'file_2': {'k0': 'v0', 'k1': 'v1'}},
                    'general': {'file_3': {'content': 'Some unparsable data'}}}
        self.assertEqual(expected, actual)

        actual = plugin_spec.service_node_process_map
        expected = {'service_2': ['node_process_0', 'node_process_1']}
        self.assertDictValueItemsEqual(expected, actual)

        actual = plugin_spec.plugin_config_items
        expected = [{'default_value': 3, 'name': 'k1', 'config_values': None,
                     'priority': 1, 'config_type': 'int', 'file': 'file_1',
                     'applicable_target': 'service_2', 'is_optional': False,
                     'scope': 'node', 'description': None},
                    {'default_value': None, 'name': 'k2',
                     'config_values': None, 'priority': 2,
                     'config_type': 'bool', 'file': 'file_1',
                     'applicable_target': 'service_2', 'is_optional': True,
                     'scope': 'cluster', 'description': None},
                    {'default_value': 'default_value_0', 'name': 'k0',
                     'config_values': None, 'priority': 2, 'file': u'file_1',
                     'config_type': 'string',
                     'applicable_target': u'service_2',
                     'is_optional': False, 'scope': u'cluster',
                     'description': 'description_0'},
                    {'default_value': None, 'name': 'k3',
                     'config_values': None, 'priority': 2,
                     'config_type': 'string', 'file': u'file_1',
                     'applicable_target': u'service_2', 'is_optional': True,
                     'scope': u'node', 'description': None},
                    {'default_value': None, 'name': 'k4',
                     'config_values': None, 'priority': 2,
                     'config_type': 'string', 'file': None,
                     'applicable_target': 'general', 'is_optional': False,
                     'scope': 'cluster', 'description': None}]
        self.assertItemsEqual(expected, actual)

        actual = plugin_spec.plugin_configs
        expected = {'service_2': {'file_1': {'k0': 'default_value_0', 'k1': 3,
                                             'k2': None, 'k3': None}},
                    'general': {None: {'k4': None}}}
        self.assertEqual(expected, actual)

        actual = plugin_spec.default_plugin_configs
        expected = {'service_2': {'file_1': {'k0': 'default_value_0', 'k1': 3,
                                             'k2': None, 'k3': None},
                                  'file_2': {'k0': 'v0', 'k1': 'v1'}},
                    'general': {None: {'k4': None},
                                'file_3': {'content': 'Some unparsable data'}}}
        self.assertEqual(expected, actual)

        actual = plugin_spec._load_plugin_config_objects()
        expected = [p.Config('k0', 'service_2', 'cluster',
                             default_value='default_value_0',
                             description='description_0'),
                    p.Config('k1', 'service_2', 'node',
                             config_type='int', default_value=3, priority=1),
                    p.Config('k2', 'service_2', 'cluster',
                             config_type='bool', is_optional=True),
                    p.Config('k3', 'service_2', 'node', is_optional=True),
                    p.Config('k4', 'general', 'cluster', is_optional=False)]
        m_actual = map(lambda i: i.to_dict(), actual)
        m_expected = map(lambda i: i.to_dict(), expected)
        self.assertItemsEqual(m_expected, m_actual)

        actual = plugin_spec.get_node_process_service('node_process_0')
        expected = 'service_2'
        self.assertEqual(expected, actual)

        actual = plugin_spec.get_default_plugin_configs(['service_2'])
        expected = {'service_2': {'file_1': {'k0': 'default_value_0', 'k1': 3,
                                             'k2': None, 'k3': None},
                                  'file_2': {'k0': 'v0', 'k1': 'v1'}}}
        self.assertEqual(expected, actual)
