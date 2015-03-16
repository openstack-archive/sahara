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

import testtools

from sahara.conductor import manager
from sahara import context
from sahara import exceptions as ex
import sahara.tests.unit.conductor.base as test_base
import sahara.tests.unit.conductor.manager.test_clusters as cluster_tests


SAMPLE_NGT = {
    "plugin_name": "test_plugin",
    "flavor_id": "42",
    "tenant_id": "tenant_1",
    "hadoop_version": "test_version",
    "name": "ngt_test",
    "node_processes": ["p1", "p2"],
    "floating_ip_pool": None,
    "availability_zone": None,
    "node_configs": {
        "service_1": {
            "config_1": "value_1"
        },
        "service_2": {
            "config_1": "value_1"
        }
    }
}

SAMPLE_CLT = {
    "plugin_name": "test_plugin",
    "tenant_id": "tenant_1",
    "hadoop_version": "test_version",
    "name": "clt_test",
    "cluster_configs": {
        "service_1": {
            "config_1": "value_1"
        },
        "service_2": {
            "config_1": "value_1"
        }
    },
    "node_groups": [
        {
            "name": "ng_1",
            "flavor_id": "42",
            "node_processes": ["p1", "p2"],
            "count": 1,
            "floating_ip_pool": None,
            "security_groups": None,
            "availability_zone": None,
        },
        {
            "name": "ng_2",
            "flavor_id": "42",
            "node_processes": ["p3", "p4"],
            "count": 3,
            "floating_ip_pool": None,
            "security_groups": ["group1", "group2"],
            "availability_zone": None,
        }

    ]
}


class NodeGroupTemplates(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(NodeGroupTemplates, self).__init__(
            checks=[
                lambda: SAMPLE_CLT,
                lambda: SAMPLE_NGT,
                lambda: manager.CLUSTER_DEFAULTS,
                lambda: manager.NODE_GROUP_DEFAULTS,
                lambda: manager.INSTANCE_DEFAULTS,
            ], *args, **kwargs)

    def test_minimal_ngt_create_list_delete(self):
        ctx = context.ctx()
        self.api.node_group_template_create(ctx, SAMPLE_NGT)

        lst = self.api.node_group_template_get_all(ctx)
        self.assertEqual(len(lst), 1)

        ngt_id = lst[0]['id']
        self.api.node_group_template_destroy(ctx, ngt_id)

        lst = self.api.node_group_template_get_all(ctx)
        self.assertEqual(len(lst), 0)

    def test_duplicate_ngt_create(self):
        ctx = context.ctx()
        self.api.node_group_template_create(ctx, SAMPLE_NGT)
        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.node_group_template_create(ctx, SAMPLE_NGT)

    def test_ngt_fields(self):
        ctx = context.ctx()
        ngt_db_obj_id = self.api.node_group_template_create(
            ctx, SAMPLE_NGT)['id']

        ngt_db_obj = self.api.node_group_template_get(ctx, ngt_db_obj_id)
        self.assertIsInstance(ngt_db_obj, dict)

        for key, val in SAMPLE_NGT.items():
            self.assertEqual(val, ngt_db_obj.get(key),
                             "Key not found %s" % key)

    def test_ngt_delete(self):
        ctx = context.ctx()
        db_obj_ngt = self.api.node_group_template_create(ctx, SAMPLE_NGT)
        _id = db_obj_ngt['id']

        self.api.node_group_template_destroy(ctx, _id)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.node_group_template_destroy(ctx, _id)

    def test_ngt_delete_default(self):
        ctx = context.ctx()
        vals = copy.copy(SAMPLE_NGT)
        vals["is_default"] = True
        db_obj_ngt = self.api.node_group_template_create(ctx, vals)
        _id = db_obj_ngt['id']

        with testtools.ExpectedException(ex.DeletionFailed):
            self.api.node_group_template_destroy(ctx, _id)

        self.api.node_group_template_destroy(ctx, _id, ignore_default=True)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.node_group_template_destroy(ctx, _id)

    def test_ngt_search(self):
        ctx = context.ctx()
        self.api.node_group_template_create(ctx, SAMPLE_NGT)

        lst = self.api.node_group_template_get_all(ctx)
        self.assertEqual(len(lst), 1)

        kwargs = {'name': SAMPLE_NGT['name'],
                  'plugin_name': SAMPLE_NGT['plugin_name']}
        lst = self.api.node_group_template_get_all(ctx, **kwargs)
        self.assertEqual(len(lst), 1)

        # Valid field but no matching value
        kwargs = {'name': SAMPLE_NGT['name']+"foo"}
        lst = self.api.node_group_template_get_all(ctx, **kwargs)
        self.assertEqual(len(lst), 0)

        # Invalid field
        lst = self.api.node_group_template_get_all(ctx, **{'badfield': 'junk'})
        self.assertEqual(len(lst), 0)

    def test_ngt_update(self):
        ctx = context.ctx()
        ngt = self.api.node_group_template_create(ctx, SAMPLE_NGT)
        ngt_id = ngt["id"]

        UPDATE_NAME = "UpdatedSampleNGTName"
        update_values = {"name": UPDATE_NAME}
        updated_ngt = self.api.node_group_template_update(ctx,
                                                          ngt_id,
                                                          update_values)
        self.assertEqual(UPDATE_NAME, updated_ngt["name"])

        updated_ngt = self.api.node_group_template_get(ctx, ngt_id)
        self.assertEqual(UPDATE_NAME, updated_ngt["name"])

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.node_group_template_update(ctx, -1, update_values)

        ngt = self.api.node_group_template_create(ctx, SAMPLE_NGT)
        ngt_id = ngt['id']
        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.node_group_template_update(ctx, ngt_id, update_values)

    def test_ngt_update_default(self):
        ctx = context.ctx()
        vals = copy.copy(SAMPLE_NGT)
        vals["is_default"] = True
        ngt = self.api.node_group_template_create(ctx, vals)
        ngt_id = ngt["id"]

        UPDATE_NAME = "UpdatedSampleNGTName"
        update_values = {"name": UPDATE_NAME}
        with testtools.ExpectedException(ex.UpdateFailedException):
            self.api.node_group_template_update(ctx,
                                                ngt_id,
                                                update_values)

        updated_ngt = self.api.node_group_template_update(ctx,
                                                          ngt_id,
                                                          update_values,
                                                          ignore_default=True)
        self.assertEqual(UPDATE_NAME, updated_ngt["name"])


class ClusterTemplates(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(ClusterTemplates, self).__init__(
            checks=[
                lambda: SAMPLE_CLT,
                lambda: SAMPLE_NGT,
                lambda: manager.CLUSTER_DEFAULTS,
                lambda: manager.NODE_GROUP_DEFAULTS,
                lambda: manager.INSTANCE_DEFAULTS,
            ], *args, **kwargs)

    def test_minimal_clt_create_list_delete(self):
        ctx = context.ctx()
        self.api.cluster_template_create(ctx, SAMPLE_CLT)

        lst = self.api.cluster_template_get_all(ctx)
        self.assertEqual(len(lst), 1)

        clt_id = lst[0]['id']
        self.api.cluster_template_destroy(ctx, clt_id)

        lst = self.api.cluster_template_get_all(ctx)
        self.assertEqual(len(lst), 0)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.cluster_template_destroy(ctx, clt_id)

    def test_duplicate_clt_create(self):
        ctx = context.ctx()
        self.api.cluster_template_create(ctx, SAMPLE_CLT)
        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.cluster_template_create(ctx, SAMPLE_CLT)

    def test_clt_fields(self):
        ctx = context.ctx()
        clt_db_obj_id = self.api.cluster_template_create(ctx, SAMPLE_CLT)['id']

        clt_db_obj = self.api.cluster_template_get(ctx, clt_db_obj_id)
        self.assertIsInstance(clt_db_obj, dict)

        for key, val in SAMPLE_CLT.items():
            if key == 'node_groups':
                # this will be checked separately
                continue
            self.assertEqual(val, clt_db_obj.get(key),
                             "Key not found %s" % key)

        for ng in clt_db_obj["node_groups"]:
            ng.pop("created_at")
            ng.pop("updated_at")
            ng.pop("id")
            ng.pop("tenant_id")
            self.assertEqual(ng.pop("cluster_template_id"), clt_db_obj_id)
            ng.pop("image_id")
            ng.pop("node_configs")
            ng.pop("node_group_template_id")
            ng.pop("volume_mount_prefix")
            ng.pop("volumes_size")
            ng.pop("volumes_per_node")
            ng.pop("volumes_availability_zone")
            ng.pop("volume_type")
            ng.pop("auto_security_group")
            ng.pop("is_proxy_gateway")
            ng.pop('volume_local_to_instance')

        self.assertEqual(SAMPLE_CLT["node_groups"],
                         clt_db_obj["node_groups"])

    def test_clt_delete(self):
        ctx = context.ctx()
        db_obj_clt = self.api.cluster_template_create(ctx, SAMPLE_CLT)
        _id = db_obj_clt['id']

        self.api.cluster_template_destroy(ctx, _id)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.cluster_template_destroy(ctx, _id)

    def test_clt_delete_default(self):
        ctx = context.ctx()
        vals = copy.copy(SAMPLE_CLT)
        vals["is_default"] = True
        db_obj_clt = self.api.cluster_template_create(ctx, vals)
        _id = db_obj_clt['id']

        with testtools.ExpectedException(ex.DeletionFailed):
            self.api.cluster_template_destroy(ctx, _id)

        self.api.cluster_template_destroy(ctx, _id, ignore_default=True)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.cluster_template_destroy(ctx, _id)

    def test_clt_search(self):
        ctx = context.ctx()
        self.api.cluster_template_create(ctx, SAMPLE_CLT)

        lst = self.api.cluster_template_get_all(ctx)
        self.assertEqual(len(lst), 1)

        kwargs = {'name': SAMPLE_CLT['name'],
                  'plugin_name': SAMPLE_CLT['plugin_name']}
        lst = self.api.cluster_template_get_all(ctx, **kwargs)
        self.assertEqual(len(lst), 1)

        # Valid field but no matching value
        kwargs = {'name': SAMPLE_CLT['name']+"foo"}
        lst = self.api.cluster_template_get_all(ctx, **kwargs)
        self.assertEqual(len(lst), 0)

        # Invalid field
        lst = self.api.cluster_template_get_all(ctx, **{'badfield': 'junk'})
        self.assertEqual(len(lst), 0)

    def test_clt_update(self):
        ctx = context.ctx()
        clt = self.api.cluster_template_create(ctx, SAMPLE_CLT)
        clt_id = clt["id"]

        UPDATE_NAME = "UpdatedClusterTemplate"
        update_values = {"name": UPDATE_NAME}
        updated_clt = self.api.cluster_template_update(ctx,
                                                       clt_id,
                                                       update_values)
        self.assertEqual(UPDATE_NAME, updated_clt["name"])

        updated_clt = self.api.cluster_template_get(ctx, clt_id)
        self.assertEqual(UPDATE_NAME, updated_clt["name"])

        # check duplicate name handling
        clt = self.api.cluster_template_create(ctx, SAMPLE_CLT)
        clt_id = clt["id"]
        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.cluster_template_update(ctx, clt_id, update_values)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.cluster_template_update(ctx, -1, update_values)

        # create a cluster and try updating the referenced cluster template
        cluster_val = copy.deepcopy(cluster_tests.SAMPLE_CLUSTER)
        cluster_val['name'] = "ClusterTempalteUpdateTestCluster"
        cluster_val['cluster_template_id'] = clt['id']
        self.api.cluster_create(ctx, cluster_val)
        update_values = {"name": "noUpdateInUseName"}

        with testtools.ExpectedException(ex.UpdateFailedException):
            self.api.cluster_template_update(ctx, clt['id'], update_values)

    def test_clt_update_default(self):
        ctx = context.ctx()
        vals = copy.copy(SAMPLE_CLT)
        vals["is_default"] = True
        clt = self.api.cluster_template_create(ctx, vals)
        clt_id = clt["id"]

        UPDATE_NAME = "UpdatedClusterTemplate"
        update_values = {"name": UPDATE_NAME}
        with testtools.ExpectedException(ex.UpdateFailedException):
            self.api.cluster_template_update(ctx,
                                             clt_id,
                                             update_values)

        updated_clt = self.api.cluster_template_update(ctx,
                                                       clt_id,
                                                       update_values,
                                                       ignore_default=True)
        self.assertEqual(UPDATE_NAME, updated_clt["name"])
