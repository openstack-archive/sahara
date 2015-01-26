# Copyright (c) 2014 Mirantis Inc.
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

from sahara.plugins.spark import config_helper as c_helper
from sahara.tests.unit import base as test_base


class ConfigHelperUtilsTest(test_base.SaharaTestCase):
    def test_make_hadoop_path(self):
        storage_paths = ['/mnt/one', '/mnt/two']
        paths = c_helper.make_hadoop_path(storage_paths, '/spam')
        expected = ['/mnt/one/spam', '/mnt/two/spam']
        self.assertEqual(expected, paths)

    @mock.patch('sahara.plugins.spark.config_helper.get_config_value')
    def test_cleanup_configs(self, get_config_value):
        getter = lambda plugin, key, cluster: plugin_configs[key]
        get_config_value.side_effect = getter
        plugin_configs = {"Minimum cleanup megabytes": 4096,
                          "Minimum cleanup seconds": 86400,
                          "Maximum cleanup seconds": 1209600}
        configs = c_helper.generate_job_cleanup_config(None)
        self.assertTrue(configs['valid'])
        expected = ["MINIMUM_CLEANUP_MEGABYTES=4096",
                    "MINIMUM_CLEANUP_SECONDS=86400",
                    "MAXIMUM_CLEANUP_SECONDS=1209600"]
        for config_value in expected:
            self.assertIn(config_value, configs['script'])
        self.assertIn("0 * * * * root /etc/hadoop/tmp-cleanup.sh",
                      configs['cron'][0])

        plugin_configs['Maximum cleanup seconds'] = 0
        configs = c_helper.generate_job_cleanup_config(None)
        self.assertFalse(configs['valid'])
        self.assertNotIn(configs, 'script')
        self.assertNotIn(configs, 'cron')

        plugin_configs = {"Minimum cleanup megabytes": 0,
                          "Minimum cleanup seconds": 0,
                          "Maximum cleanup seconds": 1209600}
        configs = c_helper.generate_job_cleanup_config(None)
        self.assertFalse(configs['valid'])
        self.assertNotIn(configs, 'script')
        self.assertNotIn(configs, 'cron')
