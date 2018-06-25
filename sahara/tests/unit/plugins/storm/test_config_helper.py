#   Copyright 2017 Massachusetts Open Cloud
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

from testtools import testcase

from sahara.plugins.storm import config_helper as s_config
from sahara.plugins.storm import plugin as s_plugin


class TestStormConfigHelper(testcase.TestCase):

    def test_generate_storm_config(self):
        STORM_101 = '1.0.1'
        STORM_110 = '1.1.0'
        tested_versions = []
        master_hostname = "s-master"
        zk_hostnames = ["s-zoo"]
        configs_101 = s_config.generate_storm_config(
            master_hostname, zk_hostnames, STORM_101)
        self.assertNotIn('nimbus.host', configs_101.keys())
        self.assertIn('nimbus.seeds', configs_101.keys())
        self.assertIn('client.jartransformer.class', configs_101.keys())
        self.assertEqual(configs_101['client.jartransformer.class'],
                         'org.apache.storm.hack.StormShadeTransformer')
        tested_versions.append(STORM_101)
        configs_110 = s_config.generate_storm_config(
            master_hostname, zk_hostnames, STORM_110)
        self.assertNotIn('nimbus.host', configs_110.keys())
        self.assertIn('nimbus.seeds', configs_110.keys())
        self.assertIn('client.jartransformer.class', configs_110.keys())
        self.assertEqual(configs_110['client.jartransformer.class'],
                         'org.apache.storm.hack.StormShadeTransformer')
        tested_versions.append(STORM_110)
        storm = s_plugin.StormProvider()
        self.assertEqual(storm.get_versions(), tested_versions)
