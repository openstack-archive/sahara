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

from savanna.db import storage as s
from savanna.openstack.common import uuidutils
from savanna.tests.unit import base


def _create_clusters(name="cluster-1", plugin_name="some_plugin",
                     hadoop_version="1.2.3", **kwargs):
    cluster_dict = {
        "name": name,
        "plugin_name": plugin_name,
        "hadoop_version": hadoop_version,
    }
    cluster_dict.update(kwargs)

    return cluster_dict, s.create_cluster(cluster_dict)


class ClusterStorageTest(base.DbTestCase):

    def test_create_cluster_trivial(self):
        cluster_dict, cluster = _create_clusters()

        self.assertIsNotNone(cluster)
        self.assertTrue(uuidutils.is_uuid_like(cluster.id))
        self.assertDictContainsSubset(cluster_dict, cluster.dict)

    def test_clusters_multi_tenancy(self):
        self.assertEqual(0, len(s.get_clusters()))

        self.set_tenant("t-1")
        self.assertEqual(0, len(s.get_clusters()))
        _create_clusters("c-1")
        _create_clusters("c-2")
        self.assertEqual(2, len(s.get_clusters()))

        self.set_tenant("t-2")
        self.assertEqual(0, len(s.get_clusters()))
        _create_clusters("c-1")
        _create_clusters("c-2")
        self.assertEqual(2, len(s.get_clusters()))
        _create_clusters("c-3")
        self.assertEqual(3, len(s.get_clusters()))
