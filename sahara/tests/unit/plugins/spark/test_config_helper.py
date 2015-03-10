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

import copy
import xml.dom.minidom as xml

import mock

from sahara.plugins.spark import config_helper as c_helper
from sahara.swift import swift_helper as swift
from sahara.tests.unit import base as test_base
from sahara.utils import xmlutils


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

    @mock.patch("sahara.swift.utils.retrieve_auth_url")
    def test_generate_xml_configs(self, auth_url):
        auth_url.return_value = "http://localhost:5000/v2/"

        # Make a dict of swift configs to verify generated values
        swift_vals = c_helper.extract_name_values(swift.get_swift_configs())

        # Make sure that all the swift configs are in core-site
        c = c_helper.generate_xml_configs({}, ['/mnt/one'], 'localhost', None)
        doc = xml.parseString(c['core-site'])
        configuration = doc.getElementsByTagName('configuration')
        properties = xmlutils.get_property_dict(configuration[0])
        self.assertDictContainsSubset(swift_vals, properties)

        # Make sure that user values have precedence over defaults
        c = c_helper.generate_xml_configs(
            {'HDFS': {'fs.swift.service.sahara.tenant': 'fred'}},
            ['/mnt/one'], 'localhost', None)
        doc = xml.parseString(c['core-site'])
        configuration = doc.getElementsByTagName('configuration')
        properties = xmlutils.get_property_dict(configuration[0])
        mod_swift_vals = copy.copy(swift_vals)
        mod_swift_vals['fs.swift.service.sahara.tenant'] = 'fred'
        self.assertDictContainsSubset(mod_swift_vals, properties)

        # Make sure that swift confgs are left out if not enabled
        c = c_helper.generate_xml_configs(
            {'HDFS': {'fs.swift.service.sahara.tenant': 'fred'},
             'general': {'Enable Swift': False}},
            ['/mnt/one'], 'localhost', None)
        doc = xml.parseString(c['core-site'])
        configuration = doc.getElementsByTagName('configuration')
        properties = xmlutils.get_property_dict(configuration[0])
        for key in mod_swift_vals.keys():
            self.assertNotIn(key, properties)
