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

import sahara.plugins.mapr.util.dict_utils as du
import sahara.plugins.mapr.util.func_utils as fu
import sahara.tests.unit.base as b


class DictUtilsTest(b.SaharaTestCase):

    def assertItemsEqual(self, expected, actual):
        for e in expected:
            self.assertIn(e, actual)
        for a in actual:
            self.assertIn(a, expected)

    def assertDictValueItemsEqual(self, expected, actual):
        self.assertItemsEqual(expected.keys(), actual.keys())
        for k in actual:
            self.assertItemsEqual(expected[k], actual[k])

    def test_append_to_key(self):
        arg_0 = {'k0': ['v0', 'v1'], 'k1': ['v1', 'v2'], 'k3': ['v3']}
        arg_1 = {'v0': {'a': 'a'}, 'v1': {'b': 'b'},
                 'v2': {'c': 'c'}, 'v4': {'d': 'd'}}
        actual = du.append_to_key(arg_0, arg_1)
        expected = {'k0': {'v0': {'a': 'a'}, 'v1': {'b': 'b'}},
                    'k1': {'v1': {'b': 'b'}, 'v2': {'c': 'c'}},
                    'k3': {}}
        self.assertEqual(expected, actual)

    def test_iterable_to_values_pair_dict_reducer(self):
        vp_dict_r = du.iterable_to_values_pair_dict_reducer
        arg = [[{'a': 'a0', 'b': 'b0', 'c': 'c0'},
                {'a': 'a1', 'b': 'b1', 'c': 'c1'}],
               [{'a': 'a2', 'b': 'b2', 'c': 'c2'}]]
        reducer = vp_dict_r('a', 'b')
        actual = reduce(reducer, arg, {})
        expected = {'a0': 'b0', 'a1': 'b1', 'a2': 'b2'}
        self.assertEqual(expected, actual)

    def test_flatten_to_list_reducer(self):
        arg = [[{'a': 'a0'}, {'a': 'a1'}], [{'a': 'a2'}]]
        reducer = du.flatten_to_list_reducer()
        actual = reduce(reducer, arg, [])
        expected = [{'a': 'a0'}, {'a': 'a1'}, {'a': 'a2'}]
        self.assertItemsEqual(expected, actual)

    def test_map_by_field_value(self):
        arg = [{'a': 'a0', 'b': 'b0', 'c': 'c0'},
               {'a': 'a0', 'b': 'b2', 'c': 'c1'},
               {'a': 'a2', 'b': 'b2', 'c': 'c2'}]

        actual = du.map_by_field_value(arg, 'a')
        expected = {'a0': [{'a': 'a0', 'b': 'b0', 'c': 'c0'},
                           {'a': 'a0', 'b': 'b2', 'c': 'c1'}],
                    'a2': [{'a': 'a2', 'b': 'b2', 'c': 'c2'}]}
        self.assertDictValueItemsEqual(expected, actual)

        actual = du.map_by_field_value(arg, 'c')
        expected = {'c0': [{'a': 'a0', 'b': 'b0', 'c': 'c0'}],
                    'c1': [{'a': 'a0', 'b': 'b2', 'c': 'c1'}],
                    'c2': [{'a': 'a2', 'b': 'b2', 'c': 'c2'}]}
        self.assertDictValueItemsEqual(expected, actual)

    def test_map_by_fields_values(self):
        arg = [{'a': 'a0', 'b': 'b0', 'c': 'c0'},
               {'a': 'a0', 'b': 'b2', 'c': 'c1'},
               {'a': 'a2', 'b': 'b2', 'c': 'c2'}]
        actual = du.map_by_fields_values(arg, ['a', 'b', 'c'])
        expected = {'a0': {'b0': {'c0': [{'a': 'a0', 'b': 'b0', 'c': 'c0'}]},
                           'b2': {'c1': [{'a': 'a0', 'b': 'b2', 'c': 'c1'}]}},
                    'a2': {'b2': {'c2': [{'a': 'a2', 'b': 'b2', 'c': 'c2'}]}}}
        self.assertItemsEqual(expected.keys(), actual.keys())
        for k0 in actual:
            self.assertItemsEqual(expected[k0].keys(), actual[k0].keys())
            for k1 in actual[k0]:
                self.assertDictValueItemsEqual(
                    expected[k0][k1], actual[k0][k1])

    def test_get_keys_by_value_type(self):
        arg = {'dict_0': {}, 'list': [], 'set': set(['elem']),
               'str': 'str', 'dict_1': {}}

        actual = du.get_keys_by_value_type(arg, dict)
        expected = ['dict_0', 'dict_1']
        self.assertItemsEqual(expected, actual)

        actual = du.get_keys_by_value_type(arg, list)
        expected = ['list']
        self.assertItemsEqual(expected, actual)

    def test_deep_update(self):
        arg_0 = {'a0': {'b0': {'c0': 'v0', 'c1': 'v1'}},
                 'a1': {'b1': 'v2'}, 'a3': 'v3'}
        arg_1 = {'a0': {'b0': {'c0': 'v1', 'c2': 'v2'}, 'b1': 'v4'},
                 'a1': 'v5', 'a3': {'v1': 'v2'}}
        actual = du.deep_update(arg_0, arg_1)
        expected = {'a0': {'b0': {'c0': 'v1', 'c1': 'v1', 'c2': 'v2'},
                           'b1': 'v4'},
                    'a1': 'v5', 'a3': {'v1': 'v2'}}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg_0)

    def test_get_keys_by_value(self):
        arg = {'k0': 'v0', 'k1': 'v0', 'k2': 'v2'}

        actual = du.get_keys_by_value(arg, 'v0')
        expected = ['k0', 'k1']
        self.assertItemsEqual(expected, actual)

        actual = du.get_keys_by_value(arg, 'v2')
        expected = ['k2']
        self.assertItemsEqual(expected, actual)

        actual = du.get_keys_by_value(arg, 'v')
        expected = []
        self.assertItemsEqual(expected, actual)

    def test_get_keys_by_value_2(self):
        arg = {'k0': ['v0', 'v1'], 'k1': ['v1', 'v2'], 'k2': ['v2', 'v3']}

        actual = du.get_keys_by_value_2(arg, 'v1')
        expected = ['k0', 'k1']
        self.assertItemsEqual(expected, actual)

        actual = du.get_keys_by_value_2(arg, 'v3')
        expected = ['k2']
        self.assertItemsEqual(expected, actual)

        actual = du.get_keys_by_value_2(arg, 'v')
        expected = []
        self.assertItemsEqual(expected, actual)

    def test_iterable_to_values_list_reducer(self):
        arg = [[{'a': 'a0', 'b': 'b0'}, {'a': 'a1', 'b': 'b0'}], [{'a': 'a2'}]]
        reducer = du.iterable_to_values_list_reducer('a')
        actual = reduce(reducer, arg, [])
        expected = ['a0', 'a1', 'a2']
        self.assertTrue(isinstance(actual, list))
        self.assertItemsEqual(expected, actual)

    def test_select(self):
        source = [{'a': 'a0', 'b': 'b0', 'c': 'c0'},
                  {'a': 'a1', 'b': 'b1', 'c': 'c0'},
                  {'a': 'a2', 'b': 'b2', 'c': 'c0'}]

        predicate = fu.like_predicate({'c': 'c0'})
        actual = du.select(['a', 'b', 'c'], source, predicate)
        expected = [{'a': 'a0', 'b': 'b0', 'c': 'c0'},
                    {'a': 'a1', 'b': 'b1', 'c': 'c0'},
                    {'a': 'a2', 'b': 'b2', 'c': 'c0'}]
        self.assertItemsEqual(expected, actual)

        predicate = fu.in_predicate('b', ['b0', 'b1'])
        actual = du.select(['a'], source, predicate)
        expected = [{'a': 'a0'}, {'a': 'a1'}]
        self.assertItemsEqual(expected, actual)

    def test_list_of_vp_dicts_function(self):
        arg = {'a0': 'b0', 'a1': 'b1'}
        actual = du.list_of_vp_dicts_function('a', 'b')(arg)
        expected = [{'a': 'a0', 'b': 'b0'}, {'a': 'a1', 'b': 'b1'}]
        self.assertTrue(isinstance(actual, list))
        for a in actual:
            self.assertTrue(isinstance(a, dict))
        self.assertItemsEqual(expected, actual)

    def test_flattened_dict(self):
        arg = {'a0': {'b0': {'c0': 'd0'}},
               'a1': {'b0': {'c1': 'd1',
                             'c2': 'd2'},
                      'b1': {'c0': 'd0'}}}

        actual = du.flattened_dict(arg, ['a', 'b', 'c', 'd'])
        expected = [{'a': 'a0', 'b': 'b0', 'c': 'c0', 'd': 'd0'},
                    {'a': 'a1', 'b': 'b0', 'c': 'c1', 'd': 'd1'},
                    {'a': 'a1', 'b': 'b0', 'c': 'c2', 'd': 'd2'},
                    {'a': 'a1', 'b': 'b1', 'c': 'c0', 'd': 'd0'}]
        self.assertItemsEqual(expected, actual)

        arg = {'a0': 'b0', 'a1': 'b1'}
        actual = du.flattened_dict(arg, ['a', 'b'])
        expected = [{'a': 'a0', 'b': 'b0'}, {'a': 'a1', 'b': 'b1'}]
        self.assertItemsEqual(expected, actual)
