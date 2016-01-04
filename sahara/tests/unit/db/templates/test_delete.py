# Copyright 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy

from sahara import context
from sahara.db.templates import api as template_api
from sahara.db.templates import utils as u
from sahara.tests.unit.conductor import base
from sahara.tests.unit.db.templates import common as c


class Config(c.Config):
    def __init__(self, option_values=None):
        option_values = option_values or {}
        if "name" not in option_values:
            option_values["name"] = "delete"
        super(Config, self).__init__(option_values)


class TemplateDeleteTestCase(base.ConductorManagerTestCase):
    def setUp(self):
        super(TemplateDeleteTestCase, self).setUp()
        self.logger = c.Logger()
        template_api.set_logger(self.logger)

    def test_node_group_template_delete_by_id(self):
        self.logger.clear_log()
        self.setup_context(tenant_id=None)
        ctx = context.ctx()
        t = self.api.node_group_template_create(ctx, c.SAMPLE_NGT)

        option_values = {"tenant_id": t["tenant_id"],
                         "id": t["id"]}
        template_api.set_conf(Config(option_values))

        template_api.do_node_group_template_delete_by_id()
        msg = 'Deleted node group template {info}'.format(
            info=u.name_and_id(t))
        self.assertIn(msg, self.logger.infos)

        t = self.api.node_group_template_get(ctx, t["id"])
        self.assertIsNone(t)

    def test_node_group_template_delete_by_id_skipped(self):
        self.logger.clear_log()
        self.setup_context(tenant_id=None)
        ctx = context.ctx()
        template_values = copy.copy(c.SAMPLE_NGT)
        template_values["is_default"] = False
        t = self.api.node_group_template_create(ctx, template_values)

        option_values = {"tenant_id": t["tenant_id"],
                         "id": t["id"]}
        template_api.set_conf(Config(option_values))

        template_api.do_node_group_template_delete_by_id()
        msg = ("Deletion of node group template {info} skipped, "
               "not a default template".format(info=u.name_and_id(t)))
        self.assertIn(msg, self.logger.warnings)

        t = self.api.node_group_template_get(ctx, t["id"])
        self.assertIsNotNone(t)

    def test_node_group_template_delete_bad_id(self):
        self.logger.clear_log()
        option_values = {"tenant_id": 1,
                         "id": "badid"}
        template_api.set_conf(Config(option_values))
        template_api.do_node_group_template_delete_by_id()
        msg = ("Deletion of node group template {id} failed, "
               "no such template".format(id=option_values["id"]))
        self.assertIn(msg, self.logger.warnings)

    def test_node_group_template_delete_by_name(self):
        self.logger.clear_log()
        ctx = context.ctx()
        t = self.api.node_group_template_create(ctx, c.SAMPLE_NGT)

        option_values = {"tenant_id": t["tenant_id"],
                         "template_name": t["name"]}
        template_api.set_conf(Config(option_values))

        template_api.do_node_group_template_delete()
        msg = 'Deleted node group template {info}'.format(
            info=u.name_and_id(t))
        self.assertIn(msg, self.logger.infos)

        t = self.api.node_group_template_get(ctx, t["id"])
        self.assertIsNone(t)

    def test_node_group_template_delete_by_name_skipped(self):
        self.logger.clear_log()
        ctx = context.ctx()
        template_values = copy.copy(c.SAMPLE_NGT)
        template_values["is_default"] = False
        t = self.api.node_group_template_create(ctx, template_values)

        option_values = {"tenant_id": t["tenant_id"],
                         "template_name": t["name"]}
        template_api.set_conf(Config(option_values))

        template_api.do_node_group_template_delete()
        msg = ("Deletion of node group template {name} failed, "
               "no such template".format(name=t["name"]))
        self.assertIn(msg, self.logger.warnings)

        t = self.api.node_group_template_get(ctx, t["id"])
        self.assertIsNotNone(t)

    def test_node_group_template_delete_in_use(self):
        self.logger.clear_log()
        ctx = context.ctx()
        t = self.api.node_group_template_create(ctx, c.SAMPLE_NGT)

        # Make a cluster that references the node group template
        cluster_values = copy.deepcopy(c.SAMPLE_CLUSTER)
        cluster_values["node_groups"][0]["node_group_template_id"] = t["id"]
        cl = self.api.cluster_create(ctx, cluster_values)

        # Make a cluster template that references the node group template
        cluster_temp_values = copy.deepcopy(c.SAMPLE_CLT)
        cluster_temp_values["node_groups"] = cluster_values["node_groups"]
        clt = self.api.cluster_template_create(ctx, cluster_temp_values)

        # Set up the expected messages
        msgs = ["Node group template {info} in use "
                "by clusters {clusters}".format(
                    info=u.name_and_id(t), clusters=[cl["name"]])]

        msgs += ["Node group template {info} in use "
                 "by cluster templates {cluster_temps}".format(
                     info=u.name_and_id(t), cluster_temps=[clt["name"]])]

        msgs += ["Deletion of node group template {info} failed".format(
            info=u.name_and_id(t))]

        # Check delete by name
        option_values = {"tenant_id": t["tenant_id"],
                         "template_name": t["name"]}
        template_api.set_conf(Config(option_values))
        template_api.do_node_group_template_delete()
        for msg in msgs:
            self.assertIn(msg, self.logger.warnings)
        self.logger.clear_log()

        # Check again with delete by id
        option_values = {"tenant_id": t["tenant_id"],
                         "id": t["id"]}
        template_api.set_conf(Config(option_values))
        template_api.do_node_group_template_delete_by_id()
        for msg in msgs:
            self.assertIn(msg, self.logger.warnings)
        self.logger.clear_log()

    def test_cluster_template_delete_by_id(self):
        self.logger.clear_log()
        self.setup_context(tenant_id=None)
        ctx = context.ctx()
        t = self.api.cluster_template_create(ctx, c.SAMPLE_CLT)

        option_values = {"tenant_id": t["tenant_id"],
                         "id": t["id"]}
        template_api.set_conf(Config(option_values))

        template_api.do_cluster_template_delete_by_id()
        msg = 'Deleted cluster template {info}'.format(
            info=u.name_and_id(t))
        self.assertIn(msg, self.logger.infos)

        t = self.api.cluster_template_get(ctx, t["id"])
        self.assertIsNone(t)

    def test_cluster_template_delete_by_id_skipped(self):
        self.logger.clear_log()
        ctx = context.ctx()
        template_values = copy.copy(c.SAMPLE_CLT)
        template_values["is_default"] = False
        t = self.api.cluster_template_create(ctx, template_values)

        option_values = {"tenant_id": t["tenant_id"],
                         "id": t["id"]}
        template_api.set_conf(Config(option_values))
        template_api.do_cluster_template_delete_by_id()
        msg = ("Deletion of cluster template {info} skipped, "
               "not a default template".format(info=u.name_and_id(t)))
        self.assertIn(msg, self.logger.warnings)

        t = self.api.cluster_template_get(ctx, t["id"])
        self.assertIsNotNone(t)

    def test_cluster_template_delete_bad_id(self):
        self.logger.clear_log()
        option_values = {"tenant_id": 1,
                         "id": "badid"}
        template_api.set_conf(Config(option_values))
        template_api.do_cluster_template_delete_by_id()
        msg = ("Deletion of cluster template {id} failed, "
               "no such template".format(id=option_values["id"]))
        self.assertIn(msg, self.logger.warnings)

    def test_cluster_template_delete_by_name(self):
        self.logger.clear_log()
        ctx = context.ctx()
        t = self.api.cluster_template_create(ctx, c.SAMPLE_NGT)

        option_values = {"tenant_id": t["tenant_id"],
                         "template_name": t["name"]}
        template_api.set_conf(Config(option_values))

        template_api.do_cluster_template_delete()
        msg = 'Deleted cluster template {info}'.format(
            info=u.name_and_id(t))
        self.assertIn(msg, self.logger.infos)

        t = self.api.cluster_template_get(ctx, t["id"])
        self.assertIsNone(t)

    def test_cluster_template_delete_by_name_skipped(self):
        self.logger.clear_log()
        ctx = context.ctx()
        template_values = copy.copy(c.SAMPLE_NGT)
        template_values["is_default"] = False
        t = self.api.cluster_template_create(ctx, template_values)

        option_values = {"tenant_id": t["tenant_id"],
                         "template_name": t["name"]}
        template_api.set_conf(Config(option_values))

        template_api.do_cluster_template_delete()
        msg = ("Deletion of cluster template {name} failed, "
               "no such template".format(name=t["name"]))
        self.assertIn(msg, self.logger.warnings)

        t = self.api.cluster_template_get(ctx, t["id"])
        self.assertIsNotNone(t)

    def test_cluster_template_delete_in_use(self):
        self.logger.clear_log()
        ctx = context.ctx()
        t = self.api.cluster_template_create(ctx, c.SAMPLE_CLT)

        # Make a cluster that references the cluster template
        cluster_values = copy.deepcopy(c.SAMPLE_CLUSTER)
        cluster_values["cluster_template_id"] = t["id"]
        del cluster_values["node_groups"]
        cl = self.api.cluster_create(ctx, cluster_values)

        # Set up the expected messages
        msgs = ["Cluster template {info} in use "
                "by clusters {clusters}".format(
                    info=u.name_and_id(t), clusters=[cl["name"]])]

        msgs += ["Deletion of cluster template {info} failed".format(
            info=u.name_and_id(t))]

        # Check delete by name
        option_values = {"tenant_id": t["tenant_id"],
                         "template_name": t["name"]}
        template_api.set_conf(Config(option_values))
        template_api.do_cluster_template_delete()
        for msg in msgs:
            self.assertIn(msg, self.logger.warnings)
        self.logger.clear_log()

        # Check again with delete by id
        option_values = {"tenant_id": t["tenant_id"],
                         "id": t["id"]}
        template_api.set_conf(Config(option_values))
        template_api.do_cluster_template_delete_by_id()
        for msg in msgs:
            self.assertIn(msg, self.logger.warnings)
        self.logger.clear_log()

    def _make_templates(self, ctx, name, plugin_name, plugin_version):
        # Make a node group template
        values = copy.copy(c.SAMPLE_NGT)
        values["name"] = "ngt_" + name
        values["plugin_name"] = plugin_name
        values["hadoop_version"] = plugin_version
        ngt = self.api.node_group_template_create(ctx, values)

        # Make a cluster template that references the node group template
        values = copy.deepcopy(c.SAMPLE_CLT)
        values["name"] = "clt_" + name
        values["plugin_name"] = plugin_name
        values["hadoop_version"] = plugin_version
        values["node_groups"][0]["node_group_template_id"] = ngt["id"]
        clt = self.api.cluster_template_create(ctx, values)

        return ngt, clt

    def test_do_delete(self):
        self.logger.clear_log()
        ctx = context.ctx()

        # Make some plugins to delete
        ngt, clt = self._make_templates(ctx, "first", "plugin", "v1")

        # Make some more for the same plugin, different version
        ngt2, clt2 = self._make_templates(ctx, "second", "plugin", "v2")

        # Make another set for a different plugin, overlapping version
        safe_ngt, safe_clt = self._make_templates(ctx, "third", "plugin2",
                                                  "v1")

        # Run a delete by plugin name/version for the first set
        option_values = {"tenant_id": ngt["tenant_id"],
                         "plugin_name": [ngt["plugin_name"]],
                         "plugin_version": [ngt["hadoop_version"]]}
        template_api.set_conf(Config(option_values))

        # Should delete clt and then ngt, check for messages in order
        template_api.do_delete()
        msgs = ["Deleted cluster template {info}".format(
            info=u.name_and_id(clt))]
        msgs += ["Deleted node group template {info}".format(
            info=u.name_and_id(ngt))]

        self.assertEqual(msgs, self.logger.infos)
        self.assertIsNone(self.api.node_group_template_get(ctx, ngt["id"]))
        self.assertIsNone(self.api.cluster_template_get(ctx, clt["id"]))

        # Make sure the other templates are still there
        self.assertIsNotNone(self.api.node_group_template_get(ctx,
                                                              ngt2["id"]))
        self.assertIsNotNone(self.api.cluster_template_get(ctx,
                                                           clt2["id"]))
        self.assertIsNotNone(self.api.node_group_template_get(ctx,
                                                              safe_ngt["id"]))
        self.assertIsNotNone(self.api.cluster_template_get(ctx,
                                                           safe_clt["id"]))

        # Run delete again for the plugin but with no version specified
        self.logger.clear_log()
        option_values = {"tenant_id": ngt2["tenant_id"],
                         "plugin_name": [ngt2["plugin_name"]],
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        # Should delete clt2 and then ngt2, check for messages in order
        template_api.do_delete()
        msgs = ["Deleted cluster template {info}".format(
            info=u.name_and_id(clt2))]
        msgs += ["Deleted node group template {info}".format(
            info=u.name_and_id(ngt2))]

        self.assertEqual(msgs, self.logger.infos)
        self.assertIsNone(self.api.node_group_template_get(ctx, ngt2["id"]))
        self.assertIsNone(self.api.cluster_template_get(ctx, clt2["id"]))

        # Make sure the other templates are still there
        self.assertIsNotNone(self.api.node_group_template_get(ctx,
                                                              safe_ngt["id"]))
        self.assertIsNotNone(self.api.cluster_template_get(ctx,
                                                           safe_clt["id"]))
