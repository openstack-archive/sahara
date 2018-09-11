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

from sahara.plugins import base as pl_base
from sahara.plugins import provisioning as pr_base
from sahara.service.api.v2 import plugins as api
from sahara.tests.unit import base
import sahara.tests.unit.service.api.v2.base as api_base


class TestPluginApi(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestPluginApi, self).setUp()
        self.calls_order = []
        self.override_config('plugins', ['fake'])
        pl_base.PLUGINS = api_base.FakePluginManager(self.calls_order)

    def test_get_plugin(self):
        # processing to dict
        data = api.get_plugin('fake', '0.1').dict
        self.assertIsNotNone(data)
        self.assertEqual(
            len(pr_base.list_of_common_configs()), len(data.get('configs')))
        self.assertEqual(['fake', '0.1'], data.get('required_image_tags'))
        self.assertEqual(
            {'HDFS': ['namenode', 'datanode']}, data.get('node_processes'))

        self.assertIsNone(api.get_plugin('fake', '0.3'))
        data = api.get_plugin('fake').dict
        self.assertIsNotNone(data.get('version_labels'))
        self.assertIsNotNone(data.get('plugin_labels'))
        del data['plugin_labels']
        del data['version_labels']

        self.assertEqual({
            'description': "Some description",
            'name': 'fake',
            'title': 'Fake plugin',
            'versions': ['0.1', '0.2']}, data)
        self.assertIsNone(api.get_plugin('name1', '0.1'))

    def test_update_plugin(self):
        data = api.get_plugin('fake', '0.1').dict
        self.assertIsNotNone(data)

        updated = api.update_plugin('fake', values={
            'plugin_labels': {'enabled': {'status': False}}}).dict
        self.assertFalse(updated['plugin_labels']['enabled']['status'])

        updated = api.update_plugin('fake', values={
            'plugin_labels': {'enabled': {'status': True}}}).dict
        self.assertTrue(updated['plugin_labels']['enabled']['status'])

        # restore to original status
        updated = api.update_plugin('fake', values={
            'plugin_labels': data['plugin_labels']}).dict
        self.assertEqual(data['plugin_labels']['enabled']['status'],
                         updated['plugin_labels']['enabled']['status'])
