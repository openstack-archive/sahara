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

import sahara.plugins.mapr.util.func_utils as fu
import sahara.tests.unit.base as b


class PredicatesTest(b.SaharaTestCase):

    def test_true_predicate(self):
        self.assertTrue(fu.true_predicate(None))

    def test_false_predicate(self):
        self.assertFalse(fu.false_predicate(None))

    def test_not_predicate(self):
        self.assertFalse(fu.not_predicate(fu.true_predicate)(None))
        self.assertTrue(fu.not_predicate(fu.false_predicate)(None))

    def test_and_predicate(self):
        true_p = fu.true_predicate
        false_p = fu.false_predicate
        and_p = fu.and_predicate
        self.assertTrue(and_p(true_p, true_p)(None))
        self.assertFalse(and_p(false_p, true_p)(None))
        self.assertFalse(and_p(true_p, false_p)(None))
        self.assertFalse(and_p(false_p, false_p)(None))

    def test_or_predicate(self):
        true_p = fu.true_predicate
        false_p = fu.false_predicate
        or_p = fu.or_predicate
        self.assertTrue(or_p(true_p, true_p)(None))
        self.assertTrue(or_p(false_p, true_p)(None))
        self.assertTrue(or_p(true_p, false_p)(None))
        self.assertFalse(or_p(false_p, false_p)(None))

    def test_field_equals_predicate(self):
        field_equals_p = fu.field_equals_predicate
        arg = {'a': 'a', 'b': 'b'}
        self.assertTrue(field_equals_p('a', 'a')(arg))
        self.assertFalse(field_equals_p('b', 'a')(arg))

    def test_like_predicate(self):
        like_p = fu.like_predicate
        arg = {'a': 'a', 'b': 'b', 'c': 'c'}
        self.assertTrue(like_p({'a': 'a', 'b': 'b', 'c': 'c'})(arg))
        self.assertTrue(like_p({'a': 'a', 'b': 'b'})(arg))
        self.assertTrue(like_p({'a': 'a'})(arg))
        self.assertTrue(like_p({'a': 'a'}, ['a'])(arg))
        self.assertTrue(like_p({})(arg))
        self.assertTrue(like_p({'a': 'a', 'b': 'b', 'c': 'a'}, ['c'])(arg))
        self.assertFalse(like_p({'a': 'a', 'b': 'b', 'c': 'a'})(arg))
        self.assertFalse(like_p({'a': 'a', 'c': 'a'})(arg))
        self.assertFalse(like_p({'c': 'a'}, ['a'])(arg))

    def test_in_predicate(self):
        in_p = fu.in_predicate
        arg = {'a': 'a', 'b': 'b'}
        self.assertTrue(in_p('a', ['a', 'b'])(arg))
        self.assertFalse(in_p('a', ['c', 'b'])(arg))
        self.assertFalse(in_p('a', [])(arg))


class FunctionsTest(b.SaharaTestCase):

    def test_copy_function(self):
        copy_f = fu.copy_function
        arg = {'a': 'a'}

        actual = copy_f()(arg)
        expected = {'a': 'a'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

    def test_append_field_function(self):
        append_field_f = fu.append_field_function
        arg = {'a': 'a'}

        actual = append_field_f('b', 'b')(arg)
        expected = {'a': 'a', 'b': 'b'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

    def test_append_fields_function(self):
        append_fields_f = fu.append_fields_function
        arg = {'a': 'a'}

        actual = append_fields_f({'b': 'b', 'c': 'c'})(arg)
        expected = {'a': 'a', 'b': 'b', 'c': 'c'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

        actual = append_fields_f({'b': 'b'})(arg)
        expected = {'a': 'a', 'b': 'b'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

        actual = append_fields_f({})(arg)
        expected = {'a': 'a'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

    def test_get_values_pair_function(self):
        get_values_pair_f = fu.get_values_pair_function
        arg = {'a': 'a', 'b': 'b'}

        actual = get_values_pair_f('a', 'b')(arg)
        expected = ('a', 'b')
        self.assertEqual(expected, actual)

    def test_get_field_function(self):
        get_field_f = fu.get_field_function
        arg = {'a': 'a', 'b': 'b'}

        actual = get_field_f('a')(arg)
        expected = ('a', 'a')
        self.assertEqual(expected, actual)

    def test_get_fields_function(self):
        get_fields_f = fu.get_fields_function
        arg = {'a': 'a', 'b': 'b'}

        actual = get_fields_f(['a', 'b'])(arg)
        expected = [('a', 'a'), ('b', 'b')]
        self.assertEqual(expected, actual)

        actual = get_fields_f(['a'])(arg)
        expected = [('a', 'a')]
        self.assertEqual(expected, actual)

    def test_extract_fields_function(self):
        extract_fields_f = fu.extract_fields_function
        arg = {'a': 'a', 'b': 'b'}

        actual = extract_fields_f(['a', 'b'])(arg)
        expected = {'a': 'a', 'b': 'b'}
        self.assertEqual(expected, actual)

        actual = extract_fields_f(['a'])(arg)
        expected = {'a': 'a'}
        self.assertEqual(expected, actual)

    def test_get_value_function(self):
        get_value_f = fu.get_value_function
        arg = {'a': 'a', 'b': 'b'}

        actual = get_value_f('a')(arg)
        expected = 'a'
        self.assertEqual(expected, actual)

    def test_set_default_value_function(self):
        set_default_value_f = fu.set_default_value_function
        arg = {'a': 'a'}

        actual = set_default_value_f('b', 'b')(arg)
        expected = {'a': 'a', 'b': 'b'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

        actual = set_default_value_f('a', 'b')(arg)
        expected = {'a': 'a'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

    def test_set_default_values_function(self):
        set_default_values_f = fu.set_default_values_function
        arg = {'a': 'a'}

        actual = set_default_values_f({'a': 'b', 'c': 'c'})(arg)
        expected = {'a': 'a', 'c': 'c'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

        actual = set_default_values_f({'b': 'b'})(arg)
        expected = {'a': 'a', 'b': 'b'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

        actual = set_default_values_f({})(arg)
        expected = {'a': 'a'}
        self.assertEqual(expected, actual)
        self.assertIsNot(actual, arg)

    def test_values_pair_to_dict_function(self):
        values_pair_to_dict_f = fu.values_pair_to_dict_function
        arg = ('a', 'b')

        actual = values_pair_to_dict_f('a', 'b')(arg)
        expected = {'a': 'a', 'b': 'b'}
        self.assertEqual(expected, actual)
