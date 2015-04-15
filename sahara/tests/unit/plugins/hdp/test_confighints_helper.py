# Copyright (c) 2015 Red Hat, Inc.
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

from sahara.plugins.hdp import confighints_helper as ch_helper
from sahara.tests.unit import base as sahara_base


SAMPLE_CONFIG = {
    'configurations': [
        {
            'tag': 'tag1.xml',
            'properties': [
                {
                    'name': 'prop1',
                    'default_value': '1234',
                    'description': 'the first property of tag1'
                },
                {
                    'name': 'prop2',
                    'default_value': '5678',
                    'description': 'the second property of tag1'
                }
            ]
        },
        {
            'tag': 'tag2.xml',
            'properties': [
                {
                    'name': 'prop3',
                    'default_value': '0000',
                    'description': 'the first property of tag2'
                }
            ]
        }
    ]
}


class ConfigHintsHelperTest(sahara_base.SaharaTestCase):
    @mock.patch(
        'sahara.plugins.hdp.confighints_helper.load_hadoop_json_for_tag',
        wraps=ch_helper.load_hadoop_json_for_tag)
    @mock.patch(
        'sahara.plugins.hdp.confighints_helper.load_json_file',
        return_value=SAMPLE_CONFIG)
    def test_get_possible_hive_config_from(self,
                                           load_json_file,
                                           load_hadoop_json_for_tag):
        expected_config = {
            'configs': [],
            'params': {}
        }
        actual_config = ch_helper.get_possible_hive_config_from(
            'sample-file-name.json')
        load_hadoop_json_for_tag.assert_called_once_with(
            'sample-file-name.json', 'hive-site.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.service.edp.oozie.workflow_creator.workflow_factory.'
        'get_possible_mapreduce_configs',
        return_value=[])
    @mock.patch(
        'sahara.plugins.hdp.confighints_helper.load_hadoop_json_for_tag',
        wraps=ch_helper.load_hadoop_json_for_tag)
    @mock.patch(
        'sahara.plugins.hdp.confighints_helper.load_json_file',
        return_value=SAMPLE_CONFIG)
    def test_get_possible_mapreduce_config_from(self,
                                                load_json_file,
                                                load_hadoop_json_for_tag,
                                                get_poss_mr_configs):
        expected_config = {
            'configs': []
        }
        actual_config = ch_helper.get_possible_mapreduce_config_from(
            'sample-file-name.json')
        load_hadoop_json_for_tag.assert_called_once_with(
            'sample-file-name.json', 'mapred-site.xml')
        get_poss_mr_configs.assert_called_once_with()
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.plugins.hdp.confighints_helper.load_hadoop_json_for_tag',
        wraps=ch_helper.load_hadoop_json_for_tag)
    @mock.patch(
        'sahara.plugins.hdp.confighints_helper.load_json_file',
        return_value=SAMPLE_CONFIG)
    def test_get_possible_pig_config_from(self,
                                          load_json_file,
                                          load_hadoop_json_for_tag):
        expected_config = {
            'configs': [],
            'args': [],
            'params': {}
        }
        actual_config = ch_helper.get_possible_pig_config_from(
            'sample-file-name.json')
        load_hadoop_json_for_tag.assert_called_once_with(
            'sample-file-name.json', 'mapred-site.xml')
        self.assertEqual(expected_config, actual_config)

    def test_get_properties_for_tag(self):
        expected_properties = [
            {
                'name': 'prop1',
                'default_value': '1234',
                'description': 'the first property of tag1'
            },
            {
                'name': 'prop2',
                'default_value': '5678',
                'description': 'the second property of tag1'
            }
        ]
        actual_properties = ch_helper.get_properties_for_tag(
            SAMPLE_CONFIG['configurations'], 'tag1.xml')
        self.assertEqual(expected_properties, actual_properties)

    @mock.patch(
        'sahara.plugins.hdp.confighints_helper.load_json_file',
        return_value=SAMPLE_CONFIG)
    def test_load_hadoop_json_for_tag(self, load_json_file):
        expected_configs = [
            {
                'name': 'prop3',
                'value': '0000',
                'description': 'the first property of tag2'
            }
        ]
        actual_configs = ch_helper.load_hadoop_json_for_tag(
            'sample-file-name.json', 'tag2.xml')
        self.assertEqual(expected_configs, actual_configs)
