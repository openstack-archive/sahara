# Copyright (c) 2015 Intel Inc.
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

from sahara.plugins.cdh import confighints_helper as ch_helper
from sahara.tests.unit import base as sahara_base


class ConfigHintsHelperTest(sahara_base.SaharaTestCase):
    @mock.patch('sahara.utils.xmlutils.load_hadoop_xml_defaults',
                return_value=[])
    def test_get_possible_hive_config_from(self, load_hadoop_xml_defaults):
        expected_config = {
            'configs': [],
            'params': {}
        }
        actual_config = ch_helper.get_possible_hive_config_from(
            'sample-config.xml')
        load_hadoop_xml_defaults.assert_called_once_with('sample-config.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch('sahara.utils.xmlutils.load_hadoop_xml_defaults',
                return_value=[])
    def test_get_possible_mapreduce_config_from(
            self, load_hadoop_xml_defaults):
        expected_config = {
            'configs': [],
        }
        actual_config = ch_helper.get_possible_mapreduce_config_from(
            'sample-config.xml')
        load_hadoop_xml_defaults.assert_any_call('sample-config.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch('sahara.utils.xmlutils.load_hadoop_xml_defaults',
                return_value=[])
    def test_get_possible_pig_config_from(
            self, load_hadoop_xml_defaults):
        expected_config = {
            'configs': [],
            'args': [],
            'params': {}
        }
        actual_config = ch_helper.get_possible_pig_config_from(
            'sample-config.xml')
        load_hadoop_xml_defaults.assert_called_once_with('sample-config.xml')
        self.assertEqual(expected_config, actual_config)
