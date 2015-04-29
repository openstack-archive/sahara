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

import mock

from sahara import conductor
from sahara import context
from sahara.tests.unit import base
from sahara.tests.unit.conductor import test_api
from sahara.utils import general


class UtilsGeneralTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(UtilsGeneralTest, self).setUp()
        self.api = conductor.API

    def _make_sample(self):
        ctx = context.ctx()
        cluster = self.api.cluster_create(ctx, test_api.SAMPLE_CLUSTER)
        return cluster

    def test_find_dict(self):
        iterable = [
            {
                "a": 1
            },
            {
                "a": 1,
                "b": 2,
                "c": 3
            },
            {
                "a": 2
            },
            {
                "c": 3
            }
        ]

        self.assertEqual({"a": 1, "b": 2, "c": 3},
                         general.find_dict(iterable, a=1, b=2))
        self.assertIsNone(general.find_dict(iterable, z=4))

    def test_find(self):
        lst = [mock.Mock(a=5), mock.Mock(b=5), mock.Mock(a=7, b=7)]
        self.assertEqual(lst[0], general.find(lst, a=5))
        self.assertEqual(lst[1], general.find(lst, b=5))
        self.assertIsNone(general.find(lst, a=8))
        self.assertEqual(lst[2], general.find(lst, a=7))
        self.assertEqual(lst[2], general.find(lst, a=7, b=7))

    def test_generate_instance_name(self):
        inst_name = "cluster-worker-001"
        self.assertEqual(
            inst_name, general.generate_instance_name("cluster", "worker", 1))
        self.assertEqual(
            inst_name, general.generate_instance_name("CLUSTER", "WORKER", 1))

    def test_get_by_id(self):
        lst = [mock.Mock(id=5), mock.Mock(id=7)]
        self.assertIsNone(general.get_by_id(lst, 9))
        self.assertEqual(lst[0], general.get_by_id(lst, 5))
        self.assertEqual(lst[1], general.get_by_id(lst, 7))

    def test_change_cluster_status(self):
        cluster = self._make_sample()
        cluster = general.change_cluster_status(cluster, "Deleting", "desc")
        self.assertEqual("Deleting", cluster.status)
        self.assertEqual("desc", cluster.status_description)
        general.change_cluster_status(cluster, "Spawning")
        self.assertEqual("Deleting", cluster.status)

    def test_change_status_description(self):
        ctx = context.ctx()
        cluster = self._make_sample()
        cluster_id = cluster.id
        cluster = general.change_cluster_status_description(cluster, "desc")
        self.assertEqual('desc', cluster.status_description)
        self.api.cluster_destroy(ctx, cluster)
        cluster = general.change_cluster_status_description(cluster_id, "desc")
        self.assertIsNone(cluster)

    def test_get_instances(self):
        cluster = self._make_sample()
        ctx = context.ctx()
        idx = 0
        ids = []
        for ng in cluster.node_groups:
            for i in range(ng.count):
                idx += 1
                ids.append(self.api.instance_add(context.ctx(), ng, {
                    'instance_id': str(idx),
                    'instance_name': str(idx),
                }))
        cluster = self.api.cluster_get(ctx, cluster)
        instances = general.get_instances(cluster, ids)
        ids = set()
        for inst in instances:
            ids.add(inst.instance_id)
        self.assertEqual(idx, len(ids))
        for i in range(1, idx):
            self.assertIn(str(i), ids)

        instances = general.get_instances(cluster)
        ids = set()
        for inst in instances:
            ids.add(inst.instance_id)
        self.assertEqual(idx, len(ids))
        for i in range(1, idx):
            self.assertIn(str(i), ids)

    def test_clean_cluster_from_empty_ng(self):
        ctx = context.ctx()
        cluster = self._make_sample()
        ng = cluster.node_groups[0]
        ng_len = len(cluster.node_groups)
        self.api.node_group_update(ctx, ng, {'count': 0})
        cluster = self.api.cluster_get(ctx, cluster.id)
        general.clean_cluster_from_empty_ng(cluster)
        cluster = self.api.cluster_get(ctx, cluster.id)
        self.assertEqual(ng_len - 1, len(cluster.node_groups))

    def test_generate_etc_hosts(self):
        cluster = self._make_sample()
        ctx = context.ctx()
        idx = 0
        for ng in cluster.node_groups:
            for i in range(ng.count):
                idx += 1
                self.api.instance_add(ctx, ng, {
                    'instance_id': str(idx),
                    'instance_name': str(idx),
                    'internal_ip': str(idx),
                })
        cluster = self.api.cluster_get(ctx, cluster)
        value = general.generate_etc_hosts(cluster)
        expected = ("127.0.0.1 localhost\n"
                    "1 1.novalocal 1\n"
                    "2 2.novalocal 2\n"
                    "3 3.novalocal 3\n"
                    "4 4.novalocal 4\n")
        self.assertEqual(expected, value)
