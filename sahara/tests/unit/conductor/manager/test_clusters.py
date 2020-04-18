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
from unittest import mock

from sqlalchemy import exc as sa_exc
import testtools

from sahara.conductor import manager
from sahara import context
from sahara.db.sqlalchemy import models as m
from sahara import exceptions as ex
import sahara.tests.unit.conductor.base as test_base
from sahara.utils import cluster as c_u


SAMPLE_CLUSTER = {
    "plugin_name": "test_plugin",
    "hadoop_version": "test_version",
    "tenant_id": "tenant_1",
    "name": "test_cluster",
    "user_keypair_id": "my_keypair",
    "node_groups": [
        {
            "name": "ng_1",
            "flavor_id": "42",
            "node_processes": ["p1", "p2"],
            "count": 1,
            "security_groups": None,
            'use_autoconfig': True,
            "shares": None
        },
        {
            "name": "ng_2",
            "flavor_id": "42",
            "node_processes": ["p3", "p4"],
            "count": 3,
            "security_groups": ["group1", "group2"],
            'use_autoconfig': True,
            "shares": None
        }
    ],
    "cluster_configs": {
        "service_1": {
            "config_2": "value_2"
        },
        "service_2": {
            "config_1": "value_1"
        }
    },
    "shares": [],
    "is_public": False,
    "is_protected": False
}


class ClusterTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(ClusterTest, self).__init__(
            checks=[
                lambda: SAMPLE_CLUSTER,
                lambda: manager.CLUSTER_DEFAULTS,
                lambda: manager.NODE_GROUP_DEFAULTS,
                lambda: manager.INSTANCE_DEFAULTS,
            ], *args, **kwargs)

    def test_cluster_create_list_update_delete(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        self.assertIsInstance(cluster_db_obj, dict)

        lst = self.api.cluster_get_all(ctx)
        self.assertEqual(1, len(lst))
        cl_id = lst[0]["id"]

        updated_cl = self.api.cluster_update(
            ctx, cl_id, {"is_public": True})
        self.assertIsInstance(updated_cl, dict)
        self.assertEqual(True, updated_cl["is_public"])

        self.api.cluster_destroy(ctx, cl_id)
        lst = self.api.cluster_get_all(ctx)
        self.assertEqual(0, len(lst))

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.cluster_destroy(ctx, cl_id)

    def test_duplicate_cluster_create(self):
        ctx = context.ctx()
        self.api.cluster_create(ctx, SAMPLE_CLUSTER)

        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.cluster_create(ctx, SAMPLE_CLUSTER)

    def test_cluster_fields(self):
        ctx = context.ctx()
        cl_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        self.assertIsInstance(cl_db_obj, dict)

        for key, val in SAMPLE_CLUSTER.items():
            if key == 'node_groups':
                # this will be checked separately
                continue
            self.assertEqual(val, cl_db_obj.get(key),
                             "Key not found %s" % key)

        for ng in cl_db_obj["node_groups"]:
            ng.pop("created_at")
            ng.pop("updated_at")
            ng.pop("id")
            self.assertEqual(cl_db_obj["id"], ng.pop("cluster_id"))
            ng.pop("image_id")
            self.assertEqual([], ng.pop("instances"))
            ng.pop("node_configs")
            ng.pop("node_group_template_id")
            ng.pop("volume_mount_prefix")
            ng.pop("volumes_size")
            ng.pop("volumes_per_node")
            ng.pop("volumes_availability_zone")
            ng.pop("volume_type")
            ng.pop("floating_ip_pool")
            ng.pop("boot_from_volume")
            ng.pop("boot_volume_type")
            ng.pop("boot_volume_availability_zone")
            ng.pop("boot_volume_local_to_instance")
            ng.pop("image_username")
            ng.pop("open_ports")
            ng.pop("auto_security_group")
            ng.pop("is_proxy_gateway")
            ng.pop("tenant_id")
            ng.pop("availability_zone")
            ng.pop('volume_local_to_instance')

        self.assertEqual(SAMPLE_CLUSTER["node_groups"],
                         cl_db_obj["node_groups"])

    def test_cluster_no_ng(self):
        ctx = context.ctx()
        cluster_schema = copy.deepcopy(SAMPLE_CLUSTER)
        cluster_schema.pop('node_groups')
        cl_db_obj = self.api.cluster_create(ctx, cluster_schema)
        self.assertIsInstance(cl_db_obj, dict)

        for key, val in cluster_schema.items():
            self.assertEqual(val, cl_db_obj.get(key),
                             "Key not found %s" % key)

        self.assertEqual([], cl_db_obj["node_groups"])

    def test_cluster_update_status(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        updated_cl = self.api.cluster_update(
            ctx, _id, {"status": c_u.CLUSTER_STATUS_ACTIVE})
        self.assertIsInstance(updated_cl, dict)
        self.assertEqual(c_u.CLUSTER_STATUS_ACTIVE, updated_cl["status"])

        get_cl_obj = self.api.cluster_get(ctx, _id)
        self.assertEqual(updated_cl, get_cl_obj)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.cluster_update(
                ctx, "bad_id", {"status": c_u.CLUSTER_STATUS_ACTIVE})

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

        self.assertEqual(2, len(cluster_db_obj["node_groups"]))
        ng_id = cluster_db_obj["node_groups"][-1]["id"]

        self.api.node_group_update(ctx, ng_id, {"image_id": "test_image"})

        cluster_db_obj = self.api.cluster_get(ctx, _id)

        found_ng = self._ng_in_cluster(cluster_db_obj, ng_id)
        self.assertTrue(found_ng, "Updated Node Group not found")

        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual("test_image", ng["image_id"])

    def test_delete_node_group(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]

        self.api.node_group_remove(ctx, ng_id)

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        found_ng = self._ng_in_cluster(cluster_db_obj, ng_id)

        self.assertFalse(found_ng, "Node Group is still in a CLuster")

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.node_group_remove(ctx, ng_id)

    def _add_instance(self, ctx, ng_id):
        instance = {
            "instance_name": "additional_vm"
        }
        return self.api.instance_add(ctx, ng_id, instance)

    def _add_instance_ipv6(self, ctx, ng_id, instance_name):
        instance = {
            "instance_name": instance_name,
            "internal_ip": "FE80:0000:0000:0000:0202:B3FF:FE1E:8329",
            "management_ip": "FE80:0000:0000:0000:0202:B3FF:FE1E:8329"
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

            ng.pop('tenant_id')
            self.assertEqual(count + 1, ng["count"])
            self.assertEqual("additional_vm",
                             ng["instances"][0]["instance_name"])

    def test_add_instance_ipv6(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]
        count = cluster_db_obj["node_groups"][-1]["count"]

        instance_name = "additional_vm_ipv6"
        self._add_instance_ipv6(ctx, ng_id, instance_name)

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            ng.pop('tenant_id')
            self.assertEqual(count + 1, ng["count"])
            self.assertEqual(instance_name,
                             ng["instances"][0]["instance_name"])

    def test_update_instance(self):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]

        instance_id = self._add_instance(ctx, ng_id)

        self.api.instance_update(ctx, instance_id,
                                 {"management_ip": "1.1.1.1"})

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual("1.1.1.1", ng["instances"][0]["management_ip"])

    def test_update_instance_ipv6(self):
        ctx = context.ctx()
        ip = "FE80:0000:0000:0000:0202:B3FF:FE1E:8329"
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        ng_id = cluster_db_obj["node_groups"][-1]["id"]

        instance_id = self._add_instance(ctx, ng_id)

        self.api.instance_update(ctx, instance_id, {"management_ip": ip})

        cluster_db_obj = self.api.cluster_get(ctx, _id)
        for ng in cluster_db_obj["node_groups"]:
            if ng["id"] != ng_id:
                continue

            self.assertEqual(ip, ng["instances"][0]["management_ip"])

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

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.instance_remove(ctx, instance_id)

    def test_cluster_search(self):
        ctx = context.ctx()
        vals = copy.deepcopy(SAMPLE_CLUSTER)
        vals['name'] = "test_name"
        self.api.cluster_create(ctx, vals)

        lst = self.api.cluster_get_all(ctx)
        self.assertEqual(1, len(lst))

        kwargs = {'name': vals['name'],
                  'plugin_name': vals['plugin_name']}
        lst = self.api.cluster_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Valid field but no matching value
        kwargs = {'name': vals['name']+'foo'}
        lst = self.api.cluster_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Valid field with substrings
        kwargs = {'name': 'test'}
        lst = self.api.cluster_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Invalid field
        self.assertRaises(sa_exc.InvalidRequestError,
                          self.api.cluster_get_all,
                          ctx, **{'badfield': 'somevalue'})

    @mock.patch('sahara.db.sqlalchemy.api.regex_filter')
    def test_cluster_search_regex(self, regex_filter):

        # do this so we can return the correct value
        def _regex_filter(query, cls, regex_cols, search_opts):
            return query, search_opts

        regex_filter.side_effect = _regex_filter

        ctx = context.ctx()
        self.api.cluster_get_all(ctx)
        self.assertEqual(0, regex_filter.call_count)

        self.api.cluster_get_all(ctx, regex_search=True, name="fox")
        self.assertEqual(1, regex_filter.call_count)
        args, kwargs = regex_filter.call_args
        self.assertIs(args[1], m.Cluster)
        self.assertEqual(args[2], ["name", "description", "plugin_name",
                                   "tenant_id"])
        self.assertEqual(args[3], {"name": "fox"})

    @mock.patch("sahara.service.edp.utils.shares.mount_shares")
    def test_cluster_update_shares(self, mount_shares):
        ctx = context.ctx()
        cluster_db_obj = self.api.cluster_create(ctx, SAMPLE_CLUSTER)
        _id = cluster_db_obj["id"]

        test_shares = [
            {
                "id": "bd71d2d5-60a0-4ed9-a3d2-ad312c368880",
                "path": "/mnt/manila",
                "access_level": "rw"
            }
        ]

        updated_cl = self.api.cluster_update(ctx, _id, {"shares": test_shares})
        self.assertIsInstance(updated_cl, dict)
        self.assertEqual(test_shares, updated_cl["shares"])

        get_cl_obj = self.api.cluster_get(ctx, _id)
        self.assertEqual(updated_cl, get_cl_obj)
