# Copyright (c) 2015 Mirantis Inc.
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

from unittest import mock

import six

from sahara import conductor as cond
from sahara import context
from sahara.plugins import recommendations_utils as ru
from sahara.tests.unit import base as b

conductor = cond.API


class Configs(object):
    def __init__(self, configs):
        self.configs = configs

    def to_dict(self):
        return self.configs


class FakeObject(object):
    def __init__(self, **kwargs):
        for attr in six.iterkeys(kwargs):
            setattr(self, attr, kwargs.get(attr))


class TestProvidingRecommendations(b.SaharaWithDbTestCase):
    @mock.patch('sahara.utils.openstack.nova.get_flavor')
    def test_get_recommended_node_configs_medium_flavor(
            self, fake_flavor):
        ng = FakeObject(flavor_id="fake_flavor", node_configs=Configs({}))
        cl = FakeObject(cluster_configs=Configs({}))
        fake_flavor.return_value = FakeObject(ram=4096, vcpus=2)
        observed = ru.HadoopAutoConfigsProvider(
            {}, [], cl, False)._get_recommended_node_configs(ng)
        self.assertEqual({
            'mapreduce.reduce.memory.mb': 768,
            'mapreduce.map.java.opts': '-Xmx307m',
            'mapreduce.map.memory.mb': 384,
            'mapreduce.reduce.java.opts': '-Xmx614m',
            'yarn.app.mapreduce.am.resource.mb': 384,
            'yarn.app.mapreduce.am.command-opts': '-Xmx307m',
            'mapreduce.task.io.sort.mb': 153,
            'yarn.nodemanager.resource.memory-mb': 3072,
            'yarn.scheduler.minimum-allocation-mb': 384,
            'yarn.scheduler.maximum-allocation-mb': 3072,
            'yarn.nodemanager.vmem-check-enabled': 'false'
        }, observed)

    @mock.patch('sahara.utils.openstack.nova.get_flavor')
    def test_get_recommended_node_configs_small_flavor(
            self, fake_flavor):
        ng = FakeObject(flavor_id="fake_flavor", node_configs=Configs({}))
        cl = FakeObject(cluster_configs=Configs({}))
        fake_flavor.return_value = FakeObject(ram=2048, vcpus=1)
        observed = ru.HadoopAutoConfigsProvider(
            {'node_configs': {}, 'cluster_configs': {}}, [], cl, False,
        )._get_recommended_node_configs(ng)
        self.assertEqual({
            'mapreduce.reduce.java.opts': '-Xmx409m',
            'yarn.app.mapreduce.am.resource.mb': 256,
            'mapreduce.reduce.memory.mb': 512,
            'mapreduce.map.java.opts': '-Xmx204m',
            'yarn.app.mapreduce.am.command-opts': '-Xmx204m',
            'mapreduce.task.io.sort.mb': 102,
            'mapreduce.map.memory.mb': 256,
            'yarn.nodemanager.resource.memory-mb': 2048,
            'yarn.scheduler.minimum-allocation-mb': 256,
            'yarn.nodemanager.vmem-check-enabled': 'false',
            'yarn.scheduler.maximum-allocation-mb': 2048,
        }, observed)

    def test_merge_configs(self):
        provider = ru.HadoopAutoConfigsProvider({}, None, None, False)
        initial_configs = {
            'cat': {
                'talk': 'meow',
            },
            'bond': {
                'name': 'james'
            }
        }

        extra_configs = {
            'dog': {
                'talk': 'woof'
            },
            'bond': {
                'extra_name': 'james bond'
            }
        }

        expected = {
            'cat': {
                'talk': 'meow',
            },
            'dog': {
                'talk': 'woof'
            },
            'bond': {
                'name': 'james',
                'extra_name': 'james bond'
            }
        }
        self.assertEqual(
            expected, provider._merge_configs(initial_configs, extra_configs))

    @mock.patch('sahara.utils.openstack.nova.get_flavor')
    @mock.patch('sahara.plugins.recommendations_utils.conductor.'
                'node_group_update')
    @mock.patch('sahara.plugins.recommendations_utils.conductor.'
                'cluster_update')
    def test_apply_recommended_configs(self, cond_cluster, cond_node_group,
                                       fake_flavor):
        class TestProvider(ru.HadoopAutoConfigsProvider):
            def get_datanode_name(self):
                return "dog_datanode"
        fake_flavor.return_value = FakeObject(ram=2048, vcpus=1)
        to_tune = {
            'cluster_configs': {
                'dfs.replication': ('dfs', 'replica')
            },
            'node_configs': {
                'mapreduce.task.io.sort.mb': ('bond', 'extra_name')
            }
        }

        fake_plugin_configs = [
            FakeObject(applicable_target='dfs', name='replica',
                       default_value=3)]
        fake_ng = FakeObject(
            use_autoconfig=True,
            count=2,
            node_processes=['dog_datanode'],
            flavor_id='fake_id',
            node_configs=Configs({
                'bond': {
                    'name': 'james'
                }
            })
        )
        fake_cluster = FakeObject(
            cluster_configs=Configs({
                'cat': {
                    'talk': 'meow',
                }
            }),
            node_groups=[fake_ng],
            use_autoconfig=True,
            extra=Configs({})
        )
        v = TestProvider(
            to_tune, fake_plugin_configs, fake_cluster, False)

        v.apply_recommended_configs()
        self.assertEqual([mock.call(context.ctx(), fake_cluster, {
            'cluster_configs': {
                'cat': {
                    'talk': 'meow'
                },
                'dfs': {
                    'replica': 2
                }
            }
        }), mock.call(
            context.ctx(), fake_cluster,
            {'extra': {'auto-configured': True}})],
            cond_cluster.call_args_list)
        self.assertEqual([mock.call(context.ctx(), fake_ng, {
            'node_configs': {
                'bond': {
                    'name': 'james',
                    'extra_name': 102
                }
            }
        })], cond_node_group.call_args_list)

    @mock.patch('sahara.utils.openstack.nova.get_flavor')
    @mock.patch('sahara.plugins.recommendations_utils.conductor.'
                'node_group_update')
    @mock.patch('sahara.plugins.recommendations_utils.conductor.'
                'cluster_update')
    def test_apply_recommended_configs_no_updates(
            self, cond_cluster, cond_node_group, fake_flavor):
        fake_flavor.return_value = FakeObject(ram=2048, vcpus=1)
        to_tune = {
            'cluster_configs': {
                'dfs.replication': ('dfs', 'replica')
            },
            'node_configs': {
                'mapreduce.task.io.sort.mb': ('bond', 'extra_name')
            }
        }

        fake_plugin_configs = [
            FakeObject(applicable_target='dfs', name='replica',
                       default_value=3)]
        fake_ng = FakeObject(
            use_autoconfig=True,
            count=2,
            node_processes=['dog_datanode'],
            flavor_id='fake_id',
            node_configs=Configs({
                'bond': {
                    'extra_name': 'james bond'
                }
            })
        )
        fake_cluster = FakeObject(
            cluster_configs=Configs({
                'dfs': {
                    'replica': 1
                }
            }),
            node_groups=[fake_ng],
            use_autoconfig=True,
            extra=Configs({})
        )
        v = ru.HadoopAutoConfigsProvider(
            to_tune, fake_plugin_configs, fake_cluster, False)
        v.apply_recommended_configs()
        self.assertEqual(0, cond_node_group.call_count)
        self.assertEqual(
            [mock.call(context.ctx(), fake_cluster,
                       {'extra': {'auto-configured': True}})],
            cond_cluster.call_args_list)

    def test_correct_use_autoconfig_value(self):
        ctx = context.ctx()
        ngt1 = conductor.node_group_template_create(ctx, {
            'name': 'ngt1',
            'flavor_id': '1',
            'plugin_name': 'vanilla',
            'hadoop_version': '1'
        })
        ngt2 = conductor.node_group_template_create(ctx, {
            'name': 'ngt2',
            'flavor_id': '2',
            'plugin_name': 'vanilla',
            'hadoop_version': '1',
            'use_autoconfig': False
        })
        self.assertTrue(ngt1.use_autoconfig)
        self.assertFalse(ngt2.use_autoconfig)
        clt = conductor.cluster_template_create(ctx, {
            'name': "clt1",
            'plugin_name': 'vanilla',
            'hadoop_version': '1',
            'node_groups': [
                {
                    'count': 3,
                    "node_group_template_id": ngt1.id
                },
                {
                    'count': 1,
                    'node_group_template_id': ngt2.id
                }
            ],
            'use_autoconfig': False
        })
        cluster = conductor.cluster_create(ctx, {
            'name': 'stupid',
            'cluster_template_id': clt.id
        })
        self.assertFalse(cluster.use_autoconfig)
        for ng in cluster.node_groups:
            if ng.name == 'ngt1':
                self.assertTrue(ng.use_autoconfig)
            else:
                self.assertFalse(ng.use_autoconfig)

    @mock.patch('sahara.plugins.recommendations_utils.conductor.'
                'cluster_update')
    def test_not_autonconfigured(self, cluster_update):
        fake_cluster = FakeObject(extra=Configs({}))
        v = ru.HadoopAutoConfigsProvider({}, [], fake_cluster, True)
        v.apply_recommended_configs()
        self.assertEqual(0, cluster_update.call_count)
