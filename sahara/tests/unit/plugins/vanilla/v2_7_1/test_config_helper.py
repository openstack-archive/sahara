# Copyright (c) 2017 EasyStack Inc.
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

from sahara.plugins import provisioning as p
from sahara.plugins.vanilla.hadoop2 import config_helper as h_helper
from sahara.plugins.vanilla.v2_7_1 import config_helper as v_helper
from sahara.tests.unit import base


class TestConfigHelper(base.SaharaTestCase):

    plugin_path = 'sahara.plugins.vanilla.v2_7_1.'
    plugin_hadoop_path = 'sahara.plugins.vanilla.hadoop2.'

    def setUp(self):
        super(TestConfigHelper, self).setUp()

    @mock.patch(plugin_hadoop_path + 'config_helper.PLUGIN_GENERAL_CONFIGS')
    @mock.patch(plugin_path + 'config_helper.PLUGIN_ENV_CONFIGS')
    @mock.patch(plugin_path + 'config_helper.PLUGIN_XML_CONFIGS')
    @mock.patch(plugin_path + 'config_helper._get_spark_configs')
    @mock.patch(plugin_path + 'config_helper._get_zookeeper_configs')
    def test_init_all_configs(self,
                              _get_zk_configs,
                              _get_spark_configs,
                              PLUGIN_XML_CONFIGS,
                              PLUGIN_ENV_CONFIGS,
                              PLUGIN_GENERAL_CONFIGS):
        configs = []
        configs.extend(PLUGIN_XML_CONFIGS)
        configs.extend(PLUGIN_ENV_CONFIGS)
        configs.extend(PLUGIN_GENERAL_CONFIGS)
        configs.extend(_get_spark_configs())
        configs.extend(_get_zk_configs())
        init_configs = v_helper._init_all_configs()
        self.assertEqual(init_configs, configs)

    def test_get_spark_configs(self):
        h_helper.SPARK_CONFS = {
            'Spark': {
                'OPTIONS': [{
                    'name': 'test',
                    'description': 'This is a test',
                    'default': 'default',
                    'priority': 1
                }]
            }
        }
        spark_configs = v_helper._get_spark_configs()
        for i in spark_configs:
            self.assertIsInstance(i, p.Config)

    def test_get_plugin_configs(self):
        self.assertEqual(v_helper.get_plugin_configs(),
                         v_helper.PLUGIN_CONFIGS)

    def test_get_xml_configs(self):
        self.assertEqual(v_helper.get_xml_configs(),
                         v_helper.PLUGIN_XML_CONFIGS)

    def test_get_env_configs(self):
        self.assertEqual(v_helper.get_env_configs(),
                         v_helper.ENV_CONFS)
