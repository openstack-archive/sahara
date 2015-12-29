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
from sahara.db.templates import utils
from sahara.tests.unit.conductor import base
from sahara.tests.unit.db.templates import common as c


class FakeNGT(object):
    def __init__(self, id):
        self.node_group_template_id = id


class FakeCluster(object):
    def __init__(self, name, node_groups=None, cluster_template_id=None):
        self.name = name
        self.node_groups = node_groups or []
        self.cluster_template_id = cluster_template_id


class TemplateUtilsTestCase(base.ConductorManagerTestCase):

    def test_substitute_ng_ids(self):
        cl = {"node_groups":
              [{"name": "worker",
                "node_group_template_id": "{vanilla-worker}",
                "count": 3},

               {"name": "master",
                "node_group_template_id": "{vanilla-master}",
                "count": 1},

               {"name": "secondary-name",
                "node_group_template_id": "some_id"}]}

        ng_dict = {"vanilla-worker": 1,
                   "vanilla-master": 2}

        utils.substitute_ng_ids(cl, ng_dict)
        self.assertEqual("1", cl["node_groups"][0]["node_group_template_id"])
        self.assertEqual("2", cl["node_groups"][1]["node_group_template_id"])
        self.assertEqual("some_id",
                         cl["node_groups"][2]["node_group_template_id"])

    def test_check_plugin_version(self):

        template = {"plugin_name": "vanilla",
                    "hadoop_version": "2.7.1"}

        self.assertTrue(utils.check_plugin_version(template, None))
        self.assertTrue(utils.check_plugin_version(template, ["2.7.1"]))
        self.assertTrue(utils.check_plugin_version(template,
                                                   ["vanilla.2.7.1"]))
        self.assertFalse(utils.check_plugin_version(template, ["1.2.1"]))

    def test_check_plugin_name_and_version(self):

        template = {"plugin_name": "vanilla",
                    "hadoop_version": "2.7.1"}

        self.assertTrue(utils.check_plugin_name_and_version(
            template, None, ["2.7.1"]))
        self.assertTrue(utils.check_plugin_name_and_version(
            template, ["vanilla"], None))
        self.assertTrue(utils.check_plugin_name_and_version(
            template, ["vanilla"], ["2.7.1"]))
        self.assertTrue(utils.check_plugin_name_and_version(
            template, ["vanilla"], ["vanilla.2.7.1"]))
        self.assertFalse(utils.check_plugin_name_and_version(
            template, ["hdp"], ["2.7.1"]))

    def test_check_node_group_template_usage(self):

        ng1 = FakeNGT(1)
        ng2 = FakeNGT(2)

        cluster = FakeCluster("cluster", [ng1])
        template = FakeCluster("template", [ng2])

        cluster_users, template_users = utils.check_node_group_template_usage(
            1, [cluster], [template])
        self.assertEqual([cluster.name], cluster_users)
        self.assertEqual([], template_users)

        cluster_users, template_users = utils.check_node_group_template_usage(
            2, [cluster], [template])
        self.assertEqual([], cluster_users)
        self.assertEqual([template.name], template_users)

    def test_check_cluster_template_usage(self):
        cluster = FakeCluster("cluster", cluster_template_id=1)

        cluster_users = utils.check_cluster_template_usage(1, [cluster])
        self.assertEqual([cluster.name], cluster_users)

    def test_find_node_group_template_by_name(self):
        ctx = context.ctx()
        t = self.api.node_group_template_create(ctx, c.SAMPLE_NGT)

        found = utils.find_node_group_template_by_name(ctx,
                                                       c.SAMPLE_NGT["name"])
        self.assertEqual(t["id"], found["id"])

        found = utils.find_node_group_template_by_name(ctx, "fred")
        self.assertIsNone(found)

    def test_find_cluster_template_by_name(self):
        ctx = context.ctx()
        t = self.api.cluster_template_create(ctx, c.SAMPLE_CLT)

        found = utils.find_cluster_template_by_name(ctx, c.SAMPLE_CLT["name"])
        self.assertEqual(t["id"], found["id"])

        found = utils.find_cluster_template_by_name(ctx, "fred")
        self.assertIsNone(found)

    def test_value_diff(self):

        current = {"cat": "meow",
                   "dog": "woof",
                   "horse": ["neigh", "whinny"]}

        new_values = {"dog": "bark",
                      "horse": "snort"}

        original = copy.deepcopy(current)
        backup = utils.value_diff(current, new_values)

        self.assertEqual({"dog": "woof",
                          "horse": ["neigh", "whinny"]}, backup)

        # current is unchanged
        self.assertEqual(original, current)
