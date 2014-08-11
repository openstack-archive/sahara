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
import StringIO as sio

import sahara.plugins.mapr.util.config_file_utils as cfu
import sahara.tests.unit.base as b

import mock as m


dirname = os.path.dirname(__file__)


class ConfigFileUtilsTest(b.SaharaTestCase):

    def assertItemsEqual(self, expected, actual):
        for e in expected:
            self.assertIn(e, actual)
        for a in actual:
            self.assertIn(a, expected)

    def test_load_properties_file(self):
        path = 'tests/unit/plugins/mapr/utils/resources/test.properties'
        actual = cfu.load_properties_file(path)
        expected = {'k0': 'v0', 'k1': 'v1'}
        self.assertEqual(expected, actual)

    def test_load_xml_file(self):
        path = 'tests/unit/plugins/mapr/utils/resources/test.xml'
        actual = cfu.load_xml_file(path)
        expected = {'k0': 'v0', 'k1': 'v1'}
        self.assertEqual(expected, actual)

    def test_load_raw_file(self):
        path = 'tests/unit/plugins/mapr/utils/resources/raw.data'
        actual = cfu.load_raw_file(path)
        expected = {'content': 'Some unparsable data'}
        self.assertEqual(expected, actual)

    @m.patch('__builtin__.open')
    def test_to_properties_file_content(self, o_mock):
        data = {'k0': 'v0', 'k1': 'v1'}
        s = sio.StringIO(cfu.to_properties_file_content(data))
        s.flush()
        o_mock.return_value = s
        actual = cfu.load_properties_file('')
        self.assertEqual(data, actual)

        data = {}
        actual = cfu.to_properties_file_content(data)
        expected = ''
        self.assertEqual(expected, actual)

    @m.patch('__builtin__.open')
    def test_to_xml_file_content(self, o_mock):
        data = {'k0': 'v0', 'k1': 'v1'}
        s = sio.StringIO(cfu.to_xml_file_content(data))
        s.flush()
        o_mock.return_value = s
        actual = cfu.load_xml_file('')
        self.assertEqual(data, actual)

    def test_to_raw_file_content(self):
        data = {'content': 'Some unparsable data'}
        actual = cfu.to_raw_file_content(data)
        expected = 'Some unparsable data'
        self.assertEqual(expected, actual)

    def test_load_file(self):
        path = 'tests/unit/plugins/mapr/utils/resources/test.properties'
        actual = cfu.load_file(path, 'properties')
        expected = {'k0': 'v0', 'k1': 'v1'}
        self.assertEqual(expected, actual)

        path = 'tests/unit/plugins/mapr/utils/resources/test.xml'
        actual = cfu.load_file(path, 'xml')
        expected = {'k0': 'v0', 'k1': 'v1'}
        self.assertEqual(expected, actual)

        path = 'tests/unit/plugins/mapr/utils/resources/raw.data'
        actual = cfu.load_file(path, 'raw')
        expected = {'content': 'Some unparsable data'}
        self.assertEqual(expected, actual)
