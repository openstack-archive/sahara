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

import six

from sahara.conductor import manager
from sahara import context
import sahara.tests.unit.conductor.base as test_base
from sahara.tests.unit.conductor.manager import test_clusters
from sahara.utils import general


class DefaultsTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(DefaultsTest, self).__init__(
            checks=[
                lambda: test_clusters.SAMPLE_CLUSTER,
                lambda: manager.CLUSTER_DEFAULTS,
                lambda: manager.NODE_GROUP_DEFAULTS,
                lambda: manager.INSTANCE_DEFAULTS,
            ], *args, **kwargs)

    def _assert_props(self, obj, **rules):
        for k, v in six.iteritems(rules):
            self.assertIn(k, obj)
            self.assertEqual(v, obj[k])

    def test_apply_defaults(self):
        self.assertEqual(
            {"a": 1, "b": 2, "c": 0},
            manager._apply_defaults({"c": 0, "b": 2},
                                    {"a": 1, "b": 2, "c": 3}))

    def _create_sample_cluster(self):
        ctx = context.ctx()
        cluster = self.api.cluster_create(ctx, test_clusters.SAMPLE_CLUSTER)
        self.assertIsInstance(cluster, dict)
        return cluster

    def test_cluster_defaults(self):
        cluster = self._create_sample_cluster()

        self._assert_props(cluster,
                           status="undefined",
                           status_description="",
                           info={})

    def test_node_group_defaults(self):
        cluster = self._create_sample_cluster()

        for ng in cluster['node_groups']:
            self._assert_props(ng,
                               node_configs={},
                               volumes_per_node=0,
                               volumes_size=0,
                               volume_mount_prefix="/volumes/disk")

    def test_instance_defaults(self):
        ctx = context.ctx()
        cluster = self._create_sample_cluster()
        cluster_id = cluster["id"]
        ng_id = cluster["node_groups"][-1]["id"]

        self.api.instance_add(ctx, ng_id, {
            "instance_name": "vm123"
        })

        cluster = self.api.cluster_get(ctx, cluster_id)
        ng = general.find_dict(cluster['node_groups'], id=ng_id)
        instance = general.find_dict(ng['instances'], instance_name="vm123")

        self._assert_props(instance, volumes=[])
