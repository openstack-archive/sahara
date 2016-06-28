# Copyright (c) 2014 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from sahara.tests.tempest.scenario.data_processing.client_tests import base


class PluginsTest(base.BaseDataProcessingTest):

    def _check_plugins_list(self):
        plugins = self.client.plugins.list()
        plugins_names = [plugin.name for plugin in plugins]
        self.assertIn('fake', plugins_names)

        return plugins_names

    def _check_plugins_get(self, plugins_names):
        for plugin_name in plugins_names:
            plugin = self.client.plugins.get(plugin_name)
            self.assertEqual(plugin_name, plugin.name)

            # check get_version_details
            for plugin_version in plugin.versions:
                detailed_plugin = self.client.plugins.get_version_details(
                    plugin_name, plugin_version)
                self.assertEqual(plugin_name, detailed_plugin.name)

                # check that required image tags contains name and version
                image_tags = detailed_plugin.required_image_tags
                self.assertIn(plugin_name, image_tags)
                self.assertIn(plugin_version, image_tags)

    def test_plugins(self):
        plugins_names = self._check_plugins_list()
        self._check_plugins_get(plugins_names)
