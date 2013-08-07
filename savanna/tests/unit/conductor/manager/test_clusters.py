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

from savanna import context
import savanna.tests.unit.conductor.manager.base as test_base


SAMPLE_CLUSTER = {
    "plugin_name": "test_plugin",
    "hadoop_version": "test_version",
    "tenant_id": "test_tenant",
    "name": "test_cluster",
    "user_keypair_id": "my_keypair",
    "node_groups": [
        {
            "name": "ng_1",
            "flavor_id": "42",
            "node_processes": ["p1", "p2"],
            "count": 1
        },
        {
            "name": "ng_2",
            "flavor_id": "42",
            "node_processes": ["p3", "p4"],
            "count": 3
        }
    ]
}


class ClusterTest(test_base.ConductorApiTestCase):

    def test_cluster_create_list_delete(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        self.assertIsInstance(cluster_db_obj, dict)

        lst = self.api.cluster_get_all(ctx)
        self.assertEqual(len(lst), 1)

        cl_id = lst[0]["id"]

        self.api.cluster_destroy(ctx, cl_id)
        lst = self.api.cluster_get_all(ctx)
        self.assertEqual(len(lst), 0)

    def test_duplicate_cluster_create(self):
        ctx = context.ctx()
        self.api.cluster_create(ctx, SAMPLE_CLUSTER)

        with self.assertRaises(RuntimeError):
            self.api.cluster_create(ctx, SAMPLE_CLUSTER)

    def test_cluster_fields(self):
        ctx = context.ctx()
        cl_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        self.assertIsInstance(cl_db_obj, dict)

        for key, val in SAMPLE_CLUSTER.items():
            if key == 'node_groups':
                #this will be checked separately
                continue
            self.assertEqual(val, cl_db_obj.get(key),
                             "Key not found %s" % key)

        for ng in cl_db_obj["node_groups"]:
            ng.pop("created_at")
            ng.pop("updated_at")
            ng.pop("id")
            self.assertEqual(ng.pop("cluster_id"), cl_db_obj["id"])
            ng.pop("image_id")
            self.assertEqual(ng.pop("instances"), [])
            ng.pop("node_configs")
            ng.pop("node_group_template_id")
            ng.pop("volume_mount_prefix")
            ng.pop("volumes_size")
            ng.pop("volumes_per_node")

        self.assertListEqual(SAMPLE_CLUSTER["node_groups"],
                             cl_db_obj["node_groups"])

    def test_cluster_update_status(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        updated_cl = self.api.cluster_update(ctx, _id, {"status": "Active"})
        self.assertIsInstance(updated_cl, dict)
        self.assertEqual(updated_cl["status"], "Active")

        get_cl_obj = self.api.cluster_get(ctx, _id)
        self.assertEqual(updated_cl, get_cl_obj)

    def _ng_in_cluster(self, cluster_db_obj, ng_id):
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] == ng_id:
                return ng
        return None

    def test_add_node_group(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        node_group = {
            "name": "ng_3",
            "flavor_id": "42",
            "node_processes": ["p3", "p4"],
            "count": 5
        }

        ng_id = self.api.node_group_add(ctx, _id, node_group)

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        found_ng = self._ng_in_cluster(cluster_db_obj, ng_id)

        self.assertTrue(found_ng, "New Node Group not found")

    def test_update_node_group(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        self.assertEqual(len(cluster_db_obj["node_groups"]), 2)
        ng_id = cluster_db_obj["node_groups"][-1]["id"]

        self.api.node_group_update(ctx, ng_id, {"image_id": "test_image"})

        cluster_db_obj = self.api.cluster_get(ctx, _id)

        found_ng = self._ng_in_cluster(cluster_db_obj, ng_id)
        self.assertTrue(found_ng, "Updated Node Group not found")

        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual(ng["image_id"], "test_image")

    def test_delete_node_group(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]

        self.api.node_group_remove(ctx, ng_id)

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        found_ng = self._ng_in_cluster(cluster_db_obj, ng_id)

        self.assertFalse(found_ng, "Node Group is still in a CLuster")

        with self.assertRaises(RuntimeError):
            self.api.node_group_remove(ctx, ng_id)

    def _add_instance(self, ctx, ng_id):
        instance = {
            "instance_name": "additional_vm"
        }
        return self.api.instance_add(ctx, ng_id, instance)

    def test_add_instance(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]
        count = cluster_db_obj["node_groups"][-1]["count"]

        self._add_instance(ctx, ng_id)

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual(count + 1, ng["count"])
            self.assertEqual("additional_vm",
                             ng["instances"][0]["instance_name"])

    def test_update_instance(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]

        instance_id = self._add_instance(ctx, ng_id)

        self.api.instance_update(context, instance_id,
                                 {"management_ip": "1.1.1.1"})

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual("1.1.1.1", ng["instances"][0]["management_ip"])

    def test_remove_instance(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]
        count = cluster_db_obj["node_groups"][-1]["count"]

        instance_id = self._add_instance(ctx, ng_id)

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual(count + 1, ng["count"])

        self.api.instance_remove(ctx, instance_id)

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual(count, ng["count"])

        with self.assertRaises(RuntimeError):
            self.api.instance_remove(ctx, instance_id)
