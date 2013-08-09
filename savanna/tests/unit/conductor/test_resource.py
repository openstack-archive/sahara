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

import copy
import unittest2

from savanna.conductor import resource as r
from savanna.utils import types

SAMPLE_DICT = {
    'first': [1, 2],
    'second': {'a': 1, 'b': 2}
}

SAMPLE_NESTED_LISTS_DICT = {
    'a': [[{'b': 123}]]
}

SAMPLE_CLUSTER_DICT = {
    'name': 'test-cluster',
    'cluster_configs': {
        'general': {
            'some_overridden_config': 'somevalue'
        }
    },
    'node_groups': [
        {
            'name': 'master',
        },
        {
            'name': 'worker',
            'node_processes': ['tasktracker', 'datanode'],
            'node_configs': {},
            'instances': [
                {
                    'name': 'test-cluster-001',
                    'ip': '1.1.1.1'
                }
            ]
        }
    ]
}


class TestResource(unittest2.TestCase):
    def test_resource_creation(self):
        res = r.Resource(SAMPLE_DICT)

        self.assertIsInstance(res.first, list)
        self.assertEqual(res.first, [1, 2])
        self.assertIsInstance(res.second, r.Resource)
        self.assertEqual(res.second.a, 1)
        self.assertEqual(res.second.b, 2)

    def test_resource_immutability(self):
        res = r.Resource(SAMPLE_DICT)

        with self.assertRaises(types.FrozenClassError):
            res.first.append(123)

        with self.assertRaises(types.FrozenClassError):
            res.first = 123

        with self.assertRaises(types.FrozenClassError):
            res.second.a = 123

    def test_nested_lists(self):
        res = r.Resource(SAMPLE_NESTED_LISTS_DICT)
        self.assertEqual(res.a[0][0].b, 123)

    def test_cluster_resource(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)

        self.assertEqual(cluster.name, 'test-cluster')

        self.assertEqual(cluster.node_groups[0].name, 'master')
        self.assertIsInstance(cluster.node_groups[0], r.NodeGroupResource)
        self.assertEqual(cluster.node_groups[0].cluster.name, 'test-cluster')

        self.assertEqual(cluster.node_groups[1].instances[0].name,
                         'test-cluster-001')
        self.assertIsInstance(cluster.node_groups[1].instances[0],
                              r.InstanceResource)
        self.assertEqual(
            cluster.node_groups[1].instances[0].node_group.name,
            'worker')

    def test_to_dict(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)
        self.assertEqual(cluster.to_dict(), SAMPLE_CLUSTER_DICT)

    def test_to_dict_filtering(self):
        cluster_dict = copy.deepcopy(SAMPLE_CLUSTER_DICT)
        cluster_dict['private_key'] = 'abacaba'
        cluster_dict['node_groups'][0]['id'] = 'some_id'

        cluster = r.ClusterResource(cluster_dict)
        self.assertEqual(cluster.to_dict(), SAMPLE_CLUSTER_DICT)

    def test_to_wrapped_dict(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)
        wrapped_dict = cluster.to_wrapped_dict()
        self.assertEqual(len(wrapped_dict), 1)
        self.assertEqual(wrapped_dict['cluster'], SAMPLE_CLUSTER_DICT)

    def test_init_doesnt_mangle_input(self):
        initial_dict = copy.deepcopy(SAMPLE_CLUSTER_DICT)
        r.ClusterResource(SAMPLE_CLUSTER_DICT)
        self.assertEqual(initial_dict, SAMPLE_CLUSTER_DICT)

    def test_re_init_doesnt_mangle_input(self):
        res = r.ClusterResource(SAMPLE_CLUSTER_DICT)

        changed_dict = copy.deepcopy(SAMPLE_CLUSTER_DICT)
        changed_dict['name'] = 'abcdcwdw'
        changed_dict_copy = copy.deepcopy(changed_dict)

        res.re_init(changed_dict)

        self.assertEqual(changed_dict, changed_dict_copy)

    def test_re_init(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)

        cluster.cluster_configs

        cluster_dict = copy.deepcopy(SAMPLE_CLUSTER_DICT)
        cluster_dict['name'] = 'somenewname'
        del cluster_dict['cluster_configs']

        cluster.re_init(cluster_dict)

        self.assertEqual('somenewname', cluster.name)
        with self.assertRaises(KeyError):
            cluster.cluster_configs
        self.assertEqual(cluster_dict, cluster.to_dict())

    def test_re_init_nested(self):
        cluster = r.ClusterResource(SAMPLE_CLUSTER_DICT)
        ng1_new_dict = copy.deepcopy(SAMPLE_CLUSTER_DICT['node_groups'][1])
        ng1_new_dict['instances'].append({
            'name': 'test_cluster_002',
            'ip': '2.2.2.2'})
        ng1_new_dict['name'] = 'new-ng-name'

        ng1 = cluster.node_groups[1]
        ng1.re_init(ng1_new_dict)

        self.assertEqual(ng1.cluster.name, cluster.name)
        self.assertEqual(cluster.node_groups[1].name, ng1.name)
        self.assertEqual(ng1.to_dict(), ng1_new_dict)
