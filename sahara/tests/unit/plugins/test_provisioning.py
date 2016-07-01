# Copyright (c) 2013 Mirantis Inc.
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

import testtools

from sahara import conductor as cond
from sahara import context
from sahara import exceptions as ex
from sahara.plugins import provisioning as p
from sahara.tests.unit import base


conductor = cond.API


class ProvisioningPluginBaseTest(testtools.TestCase):
    def test__map_to_user_inputs_success(self):
        c1, c2, c3, plugin = _build_configs_and_plugin()

        user_inputs = plugin._map_to_user_inputs(None, {
            'at-1': {
                'n-1': 'v-1',
                'n-3': 'v-3',
            },
            'at-2': {
                'n-2': 'v-2',
            },
        })

        self.assertEqual([
            p.UserInput(c1, 'v-1'),
            p.UserInput(c2, 'v-2'),
            p.UserInput(c3, 'v-3'),
        ], user_inputs)

    def test__map_to_user_inputs_failure(self):
        c1, c2, c3, plugin = _build_configs_and_plugin()

        with testtools.ExpectedException(ex.ConfigurationError):
            plugin._map_to_user_inputs(None, {
                'at-X': {
                    'n-1': 'v-1',
                },
            })

        with testtools.ExpectedException(ex.ConfigurationError):
            plugin._map_to_user_inputs(None, {
                'at-1': {
                    'n-X': 'v-1',
                },
            })


def _build_configs_and_plugin():
    c1 = p.Config('n-1', 'at-1', 'cluster')
    c2 = p.Config('n-2', 'at-2', 'cluster')
    c3 = p.Config('n-3', 'at-1', 'node')

    class TestPlugin(TestEmptyPlugin):
        def get_configs(self, hadoop_version):
            return [c1, c2, c3]

    return c1, c2, c3, TestPlugin()


class TestEmptyPlugin(p.ProvisioningPluginBase):
    def get_title(self):
        pass

    def get_versions(self):
        pass

    def get_configs(self, hadoop_version):
        pass

    def get_node_processes(self, hadoop_version):
        pass

    def configure_cluster(self, cluster):
        pass

    def start_cluster(self, cluster):
        pass


class TestPluginDataCRUD(base.SaharaWithDbTestCase):
    def test_crud(self):
        ctx = context.ctx()
        data = conductor.plugin_create(
            ctx, {'name': 'fake', 'plugin_labels': {'enabled': True}})
        self.assertIsNotNone(data)
        raised = None
        try:
            # duplicate entry, shouldn't work
            conductor.plugin_create(ctx, {'name': 'fake'})
        except Exception as e:
            raised = e
        self.assertIsNotNone(raised)

        # not duplicated entry, other tenant
        ctx.tenant = "tenant_2"
        res = conductor.plugin_create(ctx, {'name': 'fake'})
        conductor.plugin_create(ctx, {'name': 'guy'})
        self.assertIsNotNone(res)
        self.assertEqual(2, len(conductor.plugin_get_all(ctx)))

        ctx.tenant = "tenant_1"

        data = conductor.plugin_get(ctx, 'fake')
        self.assertEqual('fake', data['name'])

        data = conductor.plugin_update(
            ctx, 'fake', {'version_labels': {'0.1': {'enabled': False}}})
        data = conductor.plugin_get(ctx, 'fake')
        self.assertEqual(
            {'0.1': {'enabled': False}}, data.get('version_labels'))

        with testtools.ExpectedException(ex.NotFoundException):
            conductor.plugin_update(ctx, 'fake_not_found', {})

        data = conductor.plugin_remove(ctx, 'fake')
        self.assertIsNone(data)

        data = conductor.plugin_get(ctx, 'fake')
        self.assertIsNone(data)

        with testtools.ExpectedException(ex.NotFoundException):
            conductor.plugin_remove(ctx, 'fake')
