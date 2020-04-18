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
import tempfile
from unittest import mock

import jsonschema
from oslo_serialization import jsonutils as json
from oslo_utils import uuidutils

from sahara import context
from sahara.db.templates import api as template_api
from sahara.db.templates import utils as u
from sahara.tests.unit.conductor import base
from sahara.tests.unit.db.templates import common as c

cluster_json = {
    "plugin_name": "vanilla",
    "hadoop_version": "2.7.1",
    "node_groups": [
        {
            "name": "worker",
            "count": 3,
            "node_group_template_id": "{vanilla-260-default-worker}"
        },
        {
            "name": "master",
            "count": 1,
            "node_group_template_id": "{vanilla-260-default-master}"
        }
    ],
    "name": "vanilla-260-default-cluster",
    "neutron_management_network": "{neutron_management_network}",
    "cluster_configs": {}
}

master_json = {
    "plugin_name": "vanilla",
    "hadoop_version": "2.7.1",
    "node_processes": [
        "namenode",
        "resourcemanager",
        "hiveserver"
    ],
    "name": "vanilla-260-default-master",
    "floating_ip_pool": "{floating_ip_pool}",
    "flavor_id": "{flavor_id}",
    "auto_security_group": "{auto_security_group}",
    'security_groups': "{security_groups}"
}

worker_json = {
    "plugin_name": "vanilla",
    "hadoop_version": "2.7.1",
    "node_processes": [
        "nodemanager",
        "datanode"
    ],
    "name": "vanilla-260-default-worker",
    "floating_ip_pool": "{floating_ip_pool}",
    "flavor_id": "{flavor_id}",
    "auto_security_group": "{auto_security_group}",
    'security_groups': "{security_groups}"
}


class Config(c.Config):
    def __init__(self, option_values=None):
        option_values = option_values or {}
        if "name" not in option_values:
            option_values["name"] = "update"
        super(Config, self).__init__(option_values)


class TemplateUpdateTestCase(base.ConductorManagerTestCase):
    def setUp(self):
        super(TemplateUpdateTestCase, self).setUp()
        self.logger = c.Logger()
        template_api.set_logger(self.logger)

    @mock.patch("sahara.utils.api_validator.ApiValidator.validate")
    def test_check_cluster_templates_valid(self, validate):
        self.logger.clear_log()
        ng_templates = [{"template": c.SAMPLE_NGT,
                         "path": "/foo"}]

        # Reference the node group template by name
        clt = copy.copy(c.SAMPLE_CLT)
        clt["node_groups"] = [
            {"name": "test",
             "count": 1,
             "node_group_template_id": "{%s}" % c.SAMPLE_NGT["name"]}
        ]
        cl_templates = [{"template": clt,
                         "path": "/bar"}]

        # Test failed validation
        validate.side_effect = jsonschema.ValidationError("mistake")
        res = template_api.check_cluster_templates_valid(ng_templates,
                                                         cl_templates)
        self.assertTrue(res)
        msg = "Validation for /bar failed, mistake"
        self.assertIn(msg, self.logger.warnings)

        # Validation passes, name replaced
        validate.side_effect = None
        self.logger.clear_log()
        res = template_api.check_cluster_templates_valid(ng_templates,
                                                         cl_templates)
        self.assertFalse(res)
        node_groups = validate.call_args[0][0]["node_groups"]
        self.assertTrue(uuidutils.is_uuid_like(
            node_groups[0]["node_group_template_id"]))

    def test_add_config_section(self):
        # conf here can't be a mock.Mock() because hasattr will
        # return true
        conf = Config()
        conf.register_group = mock.Mock()
        conf.register_opts = mock.Mock()

        template_api.set_conf(conf)
        opts = ["option"]

        # Named config section
        template_api.add_config_section("section", opts)

        self.assertEqual(1, conf.register_group.call_count)
        config_group = conf.register_group.call_args[0][0]
        self.assertEqual("section", config_group.name)
        self.assertEqual([
            mock.call(opts, config_group)], conf.register_opts.call_args_list)

        conf.register_group.reset_mock()
        conf.register_opts.reset_mock()

        # No config section, opts should be registered against
        # the default section
        template_api.add_config_section(None, opts)

        conf.register_group.assert_not_called()
        conf.register_opts.assert_called_with(opts)

    @mock.patch("sahara.db.templates.api.add_config_section")
    def test_add_config_section_for_template(self, add_config_section):

        conf = mock.Mock()
        conf.list_all_sections = mock.Mock()
        template_api.set_conf(conf)

        # No config sections
        conf.list_all_sections.return_value = []
        ngt = c.SAMPLE_NGT
        template_api.add_config_section_for_template(ngt)
        add_config_section.assert_called_with(None,
                                              template_api.all_template_opts)
        add_config_section.reset_mock()

        # Add config section matching plugin
        conf.list_all_sections.return_value += [ngt["plugin_name"]]
        template_api.add_config_section_for_template(ngt)
        add_config_section.assert_called_with(ngt["plugin_name"],
                                              template_api.all_template_opts)
        add_config_section.reset_mock()

        # Add config section matching plugin and version
        section = "{plugin_name}_{hadoop_version}".format(**ngt)
        conf.list_all_sections.return_value += [section]
        template_api.add_config_section_for_template(ngt)
        add_config_section.assert_called_with(section,
                                              template_api.all_template_opts)
        add_config_section.reset_mock()

        # Add config section matching plugin, version and name
        section = "{plugin_name}_{hadoop_version}_{name}".format(**ngt)
        conf.list_all_sections.return_value += [section]
        template_api.add_config_section_for_template(ngt)
        add_config_section.assert_called_with(
            section,
            template_api.node_group_template_opts)
        add_config_section.reset_mock()

        # Add config section matching name
        section = "{name}".format(**ngt)
        conf.list_all_sections.return_value += [section]
        template_api.add_config_section_for_template(ngt)
        add_config_section.assert_called_with(
            section,
            template_api.node_group_template_opts)
        add_config_section.reset_mock()

    def test_substitute_config_values_ngt(self):
        ngt = copy.copy(c.SAMPLE_NGT)
        ngt["flavor_id"] = "{flavor_id}"
        ngt["floating_ip_pool"] = "{floating_ip_pool}"
        configs = {"flavor_id": "2",
                   "floating_ip_pool": None}
        template_api.substitute_config_values(configs, ngt, "/path")
        self.assertEqual("2", ngt["flavor_id"])
        self.assertIsNone(ngt["floating_ip_pool"])

    def test_substitute_config_values_clt(self):
        clt = copy.copy(c.SAMPLE_CLT)
        clt["neutron_management_network"] = "{neutron_management_network}"
        clt["default_image_id"] = "{default_image_id}"

        netid = uuidutils.generate_uuid()
        configs = {"neutron_management_network": netid,
                   "default_image_id": None}
        template_api.substitute_config_values(configs, clt, "/path")
        self.assertEqual(netid, clt["neutron_management_network"])
        self.assertIsNone(clt["default_image_id"])

    def _write_files(self, tempdir, templates):
        files = []
        for template in templates:
            fp = tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                             dir=tempdir, delete=False)
            json.dump(template, fp)
            files.append(fp.name)
            fp.close()
        return files

    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_process_files(self, add_config_section, get_configs):
        self.logger.clear_log()
        tempdir = tempfile.mkdtemp()

        # This should be ignored by process files
        some_other_json = {"name": "fred",
                           "description": "not a template"}

        files = self._write_files(
            tempdir, [cluster_json, master_json, worker_json, some_other_json])

        get_configs.return_value = {"flavor_id": '2', 'security_groups': [],
                                    'auto_security_group': False}
        option_values = {"plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        # Check that cluster and ng templates are read and returned
        ng_templates, cl_templates = template_api.process_files(tempdir, files)
        cl_temp_names = [f["template"]["name"] for f in cl_templates]
        ng_temp_names = [f["template"]["name"] for f in ng_templates]
        self.assertEqual([cluster_json["name"]], cl_temp_names)
        self.assertEqual([master_json["name"],
                          worker_json["name"]], ng_temp_names)

        # Plugin name/version filtering applied
        option_values = {"plugin_name": "vanilla",
                         "plugin_version": "2.7.1"}
        template_api.set_conf(Config(option_values))
        ng_templates, cl_templates = template_api.process_files(tempdir, files)
        self.assertEqual(1, len(cl_templates))
        self.assertEqual(2, len(ng_templates))

        option_values = {"plugin_name": "hdp",
                         "plugin_version": "2.7.1"}
        template_api.set_conf(Config(option_values))
        ng_templates, cl_templates = template_api.process_files(tempdir, files)
        self.assertEqual(0, len(cl_templates))
        self.assertEqual(0, len(ng_templates))

    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_process_files_validation_error(self, add_config_section,
                                            get_configs):
        self.logger.clear_log()
        tempdir = tempfile.mkdtemp()

        files = self._write_files(
            tempdir, [cluster_json, master_json, worker_json])

        get_configs.return_value = {
            "flavor_id": '2',
            'security_groups': [],
            'auto_security_group': False
        }

        option_values = {"plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        # Bad JSON validation for ng should cause all files to be skipped
        bad_worker = copy.copy(worker_json)
        bad_worker["my_dog"] = ["fido"]
        new_file = self._write_files(tempdir, [bad_worker])[0]
        ng_templates, cl_templates = template_api.process_files(
            tempdir, files + [new_file])
        self.assertEqual(0, len(ng_templates))
        self.assertEqual(0, len(cl_templates))
        msg = ("Validation for {path} failed, "
               "Additional properties are not allowed".format(path=new_file))
        self.assertTrue(self.logger.warnings[0].startswith(msg))

    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_process_files_bad_json(self, add_config_section, get_configs):
        self.logger.clear_log()
        tempdir = tempfile.mkdtemp()

        files = self._write_files(
            tempdir, [cluster_json, master_json, worker_json])

        get_configs.return_value = {"flavor_id": '2', 'security_groups': [],
                                    'auto_security_group': False}
        option_values = {"plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        # Invalid JSON should cause all files to be skipped
        fp = tempfile.NamedTemporaryFile(suffix=".json",
                                         dir=tempdir, delete=False)
        fp.write(b"not json")
        files += [fp.name]
        fp.close()
        ng_templates, cl_templates = template_api.process_files(tempdir, files)
        self.assertEqual(0, len(ng_templates))
        self.assertEqual(0, len(cl_templates))
        msg = ("Error processing {name}".format(name=files[-1]))
        self.assertTrue(self.logger.warnings[0].startswith(msg))
        msg = ("Skipping processing for {dir}, "
               "error processing files".format(dir=tempdir))
        self.assertEqual(msg, self.logger.warnings[1])

    def test_add_node_group_templates(self):
        self.logger.clear_log()
        ctx = context.ctx()

        # Create a record that will be updated in the db
        existing = copy.copy(c.SAMPLE_NGT)
        existing = self.api.node_group_template_create(ctx, existing)

        # Create the update
        update = copy.copy(c.SAMPLE_NGT)
        update["flavor_id"] = "6"

        # Create a record that will be new in the db
        new = copy.copy(c.SAMPLE_NGT)
        new["name"] = "new_name"

        ngts = [{"template": update, "path": "foo"},
                {"template": new, "path": "bar"}]

        ng_info, error = template_api.add_node_group_templates(ctx, ngts)
        self.assertFalse(error)

        new = self.api.node_group_template_get_all(ctx, name=new["name"])[0]
        self.assertIsNotNone(new)

        # ng_info["created"] is a list of templates that were created
        self.assertEqual(1, len(ng_info["created"]))
        self.assertEqual(new["id"], ng_info["created"][0]["id"])

        # ng_info["updated"] is a list of tuples for templates that
        # were updated.  First element in the tuple is the template,
        # second is a dictionary of fields that were updated.
        self.assertEqual(1, len(ng_info["updated"]))
        self.assertEqual(existing["id"], ng_info["updated"][0][0]["id"])
        self.assertEqual({"flavor_id": "42"}, ng_info["updated"][0][1])

        # ng_info["dict"] is a dictionary of name/id pairs
        self.assertEqual({new["name"]: new["id"],
                          existing["name"]: existing["id"]}, ng_info["ids"])

        msg = ("Created node group template {info} from bar".format(
            info=u.name_and_id(new)))
        self.assertIn(msg, self.logger.infos)

        msg = ("Updated node group template {info} from foo".format(
            info=u.name_and_id(existing)))
        self.assertIn(msg, self.logger.infos)

        self.api.node_group_template_destroy(ctx, new["id"],
                                             ignore_prot_on_def=True)
        self.api.node_group_template_destroy(ctx, existing["id"],
                                             ignore_prot_on_def=True)

    @mock.patch("sahara.conductor.API.node_group_template_update")
    @mock.patch("sahara.db.templates.api.reverse_node_group_template_creates")
    @mock.patch("sahara.db.templates.api.reverse_node_group_template_updates")
    def test_add_node_group_templates_update_failed(self,
                                                    reverse_updates,
                                                    reverse_creates,
                                                    ng_update):
        self.logger.clear_log()
        ctx = context.ctx()

        ng_update.side_effect = Exception("mistake")

        # Create a record that will be updated in the db
        existing = copy.copy(c.SAMPLE_NGT)
        existing = self.api.node_group_template_create(ctx, existing)

        # Create the update
        update = copy.copy(c.SAMPLE_NGT)
        update["flavor_id"] = "6"

        # Create a record that will be new in the db
        new = copy.copy(c.SAMPLE_NGT)
        new["name"] = "new_name"

        ngts = [{"template": new, "path": "bar"},
                {"template": update, "path": "foo"}]

        ng_info, error = template_api.add_node_group_templates(ctx, ngts)
        new = self.api.node_group_template_get_all(ctx, name=new["name"])[0]
        self.assertTrue(error)
        self.assertEqual(1, reverse_creates.call_count)

        # call should have been (ctx, [new])
        self.assertEqual(new["id"], reverse_creates.call_args[0][1][0]["id"])

        self.assertEqual(1, reverse_updates.call_count)
        msg = ("Update of node group template {info} failed, mistake".format(
            info=u.name_and_id(existing)))
        self.assertIn(msg, self.logger.warnings)

        self.api.node_group_template_destroy(ctx, new["id"],
                                             ignore_prot_on_def=True)
        self.api.node_group_template_destroy(ctx, existing["id"],
                                             ignore_prot_on_def=True)

    @mock.patch("sahara.conductor.API.node_group_template_create")
    @mock.patch("sahara.db.templates.api.reverse_node_group_template_creates")
    @mock.patch("sahara.db.templates.api.reverse_node_group_template_updates")
    def test_add_node_group_templates_create_failed(self,
                                                    reverse_updates,
                                                    reverse_creates,
                                                    ng_create):
        self.logger.clear_log()
        ctx = context.ctx()

        ng_create.side_effect = Exception("mistake")

        # Create a record that will be updated in the db
        existing = copy.copy(c.SAMPLE_NGT)
        existing = self.api.node_group_template_create(ctx, existing)

        # Create the update
        update = copy.copy(c.SAMPLE_NGT)
        update["flavor_id"] = "6"

        # Create a record that will be new in the db
        new = copy.copy(c.SAMPLE_NGT)
        new["name"] = "new_name"

        ngts = [{"template": update, "path": "foo"},
                {"template": new, "path": "bar"}]

        ng_info, error = template_api.add_node_group_templates(ctx, ngts)
        self.assertTrue(error)
        self.assertEqual(1, reverse_creates.call_count)
        self.assertEqual(1, reverse_updates.call_count)

        # call should have been (ctx, [(existing, updated_fields)])
        self.assertEqual({"flavor_id": existing["flavor_id"]},
                         reverse_updates.call_args[0][1][0][1])

        msg = "Creation of node group template from bar failed, mistake"
        self.assertIn(msg, self.logger.warnings)

        self.api.node_group_template_destroy(ctx, existing["id"],
                                             ignore_prot_on_def=True)

    def test_add_cluster_templates(self):
        self.logger.clear_log()
        ctx = context.ctx()

        # Create a record that will be updated in the db
        existing = copy.copy(c.SAMPLE_CLT)
        existing = self.api.cluster_template_create(ctx, existing)

        # Create the update
        update = copy.copy(c.SAMPLE_CLT)
        update["hadoop_version"] = "1"

        # Create a record that will be new in the db
        new = copy.copy(c.SAMPLE_CLT)
        new["name"] = "new_name"

        clts = [{"template": update, "path": "foo"},
                {"template": new, "path": "bar"}]

        error = template_api.add_cluster_templates(ctx, clts, {})
        self.assertFalse(error)

        new = self.api.cluster_template_get_all(ctx, name=new["name"])[0]
        self.assertIsNotNone(new)

        msg = ("Created cluster template {info} from bar".format(
            info=u.name_and_id(new)))
        self.assertIn(msg, self.logger.infos)

        msg = ("Updated cluster template {info} from foo".format(
            info=u.name_and_id(existing)))
        self.assertIn(msg, self.logger.infos)

        self.api.cluster_template_destroy(ctx, new["id"],
                                          ignore_prot_on_def=True)
        self.api.cluster_template_destroy(ctx, existing["id"],
                                          ignore_prot_on_def=True)

    @mock.patch("sahara.conductor.API.cluster_template_update")
    @mock.patch("sahara.db.templates.api.reverse_cluster_template_creates")
    @mock.patch("sahara.db.templates.api.reverse_cluster_template_updates")
    def test_add_cluster_templates_update_failed(self,
                                                 reverse_updates,
                                                 reverse_creates,
                                                 cl_update):
        self.logger.clear_log()
        ctx = context.ctx()

        cl_update.side_effect = Exception("mistake")

        # Create a record that will be updated in the db
        existing = copy.copy(c.SAMPLE_CLT)
        existing = self.api.cluster_template_create(ctx, existing)

        # Create the update
        update = copy.copy(c.SAMPLE_CLT)
        update["hadoop_version"] = "1"

        # Create a record that will be new in the db
        new = copy.copy(c.SAMPLE_CLT)
        new["name"] = "new_name"

        clts = [{"template": new, "path": "bar"},
                {"template": update, "path": "foo"}]

        error = template_api.add_cluster_templates(ctx, clts, {})
        new = self.api.cluster_template_get_all(ctx, name=new["name"])[0]
        self.assertTrue(error)
        self.assertEqual(1, reverse_creates.call_count)

        # call should have been (ctx, [new])
        self.assertEqual(new["id"], reverse_creates.call_args[0][1][0]["id"])

        self.assertEqual(1, reverse_updates.call_count)
        msg = ("Update of cluster template {info} failed, mistake".format(
            info=u.name_and_id(existing)))
        self.assertIn(msg, self.logger.warnings)

        self.api.cluster_template_destroy(ctx, new["id"],
                                          ignore_prot_on_def=True)
        self.api.cluster_template_destroy(ctx, existing["id"],
                                          ignore_prot_on_def=True)

    @mock.patch("sahara.conductor.API.cluster_template_create")
    @mock.patch("sahara.db.templates.api.reverse_cluster_template_creates")
    @mock.patch("sahara.db.templates.api.reverse_cluster_template_updates")
    def test_add_cluster_templates_create_failed(self,
                                                 reverse_updates,
                                                 reverse_creates,
                                                 cl_create):
        self.logger.clear_log()
        ctx = context.ctx()

        cl_create.side_effect = Exception("mistake")

        # Create a record that will be updated in the db
        existing = copy.copy(c.SAMPLE_CLT)
        existing = self.api.cluster_template_create(ctx, existing)

        # Create the update
        update = copy.copy(c.SAMPLE_CLT)
        update["hadoop_version"] = "1"

        # Create a record that will be new in the db
        new = copy.copy(c.SAMPLE_CLT)
        new["name"] = "new_name"

        clts = [{"template": update, "path": "foo"},
                {"template": new, "path": "bar"}]

        error = template_api.add_cluster_templates(ctx, clts, {})
        self.assertTrue(error)
        self.assertEqual(1, reverse_creates.call_count)
        self.assertEqual(1, reverse_updates.call_count)

        # call should have been (ctx, [(existing, updated_fields)])
        # updated fields will contain hadoop_version and node_groups,
        # since node_groups is modified by the conductor
        updated_fields = reverse_updates.call_args[0][1][0][1]
        self.assertEqual(updated_fields["hadoop_version"],
                         existing["hadoop_version"])
        self.assertIn("node_groups", updated_fields)

        msg = "Creation of cluster template from bar failed, mistake"
        self.assertIn(msg, self.logger.warnings)

        self.api.cluster_template_destroy(ctx, existing["id"],
                                          ignore_prot_on_def=True)

    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_do_update_trash(self, add_config, get_configs):
        self.logger.clear_log()
        ctx = context.ctx()

        tempdir = tempfile.mkdtemp()

        self._write_files(tempdir, [cluster_json, master_json, worker_json])

        get_configs.return_value = {
            "flavor_id": '2',
            "neutron_management_network": uuidutils.generate_uuid(),
            'auto_security_group': True,
            'security_groups': [],
        }

        option_values = {"tenant_id": ctx.tenant_id,
                         "directory": tempdir,
                         "norecurse": None,
                         "plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))
        template_api.do_update()

        ngs = self.api.node_group_template_get_all(ctx)
        ng_names = sorted([ng["name"] for ng in ngs])
        self.assertEqual(sorted([master_json["name"], worker_json["name"]]),
                         ng_names)

        clts = self.api.cluster_template_get_all(ctx)
        clt_names = sorted([clt["name"] for clt in clts])
        clts = self.api.cluster_template_get_all(ctx)
        self.assertEqual([cluster_json["name"]], clt_names)

    @mock.patch("sahara.db.templates.api.check_cluster_templates_valid")
    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_do_update_cluster_invalid(self, add_config,
                                       get_configs, clt_valid):
        self.logger.clear_log()
        ctx = context.ctx()

        tempdir = tempfile.mkdtemp()

        self._write_files(tempdir, [cluster_json, master_json, worker_json])

        get_configs.return_value = {
            "flavor_id": '2',
            "neutron_management_network": uuidutils.generate_uuid()
        }

        option_values = {"tenant_id": ctx.tenant_id,
                         "directory": tempdir,
                         "norecurse": None,
                         "plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        clt_valid.return_value = True

        template_api.do_update()

        ngs = self.api.node_group_template_get_all(ctx)
        self.assertEqual([], ngs)

        clts = self.api.cluster_template_get_all(ctx)
        self.assertEqual([], clts)

        msg = ("Skipping processing for {dir}, "
               "error processing cluster templates".format(dir=tempdir))
        self.assertIn(msg, self.logger.warnings)

    @mock.patch("sahara.db.templates.api.check_usage_of_existing")
    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_do_update_existing_fails(self, add_config,
                                      get_configs, check_existing):
        self.logger.clear_log()
        ctx = context.ctx()

        tempdir = tempfile.mkdtemp()

        self._write_files(tempdir, [cluster_json, master_json, worker_json])

        get_configs.return_value = {
            "flavor_id": '2',
            "neutron_management_network": uuidutils.generate_uuid()
        }
        option_values = {"tenant_id": ctx.tenant_id,
                         "directory": tempdir,
                         "norecurse": None,
                         "plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        check_existing.return_value = True

        template_api.do_update()

        ngs = self.api.node_group_template_get_all(ctx)
        self.assertEqual([], ngs)

        clts = self.api.cluster_template_get_all(ctx)
        self.assertEqual([], clts)

        msg = ("Skipping processing for {dir}, "
               "templates in use".format(dir=tempdir))
        self.assertIn(msg, self.logger.warnings)

    @mock.patch("sahara.db.templates.api.add_node_group_templates")
    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_do_update_add_ngts_fails(self, add_config,
                                      get_configs, add_ngts):
        self.logger.clear_log()
        ctx = context.ctx()

        tempdir = tempfile.mkdtemp()

        self._write_files(tempdir, [cluster_json, master_json, worker_json])

        get_configs.return_value = {
            "flavor_id": '2',
            "neutron_management_network": uuidutils.generate_uuid()
        }

        option_values = {"tenant_id": ctx.tenant_id,
                         "directory": tempdir,
                         "norecurse": None,
                         "plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        add_ngts.return_value = ({}, True)

        template_api.do_update()

        ngs = self.api.node_group_template_get_all(ctx)
        self.assertEqual([], ngs)

        clts = self.api.cluster_template_get_all(ctx)
        self.assertEqual([], clts)

        msg = ("Skipping processing for {dir}, "
               "error processing node group templates".format(dir=tempdir))
        self.assertIn(msg, self.logger.warnings)

    @mock.patch("sahara.db.templates.api.reverse_node_group_template_creates")
    @mock.patch("sahara.db.templates.api.reverse_node_group_template_updates")
    @mock.patch("sahara.db.templates.api.add_cluster_templates")
    @mock.patch("sahara.db.templates.api.get_configs")
    @mock.patch("sahara.db.templates.api.add_config_section_for_template")
    def test_do_update_add_clts_fails(self,
                                      add_config,
                                      get_configs,
                                      add_clts,
                                      reverse_ng_updates,
                                      reverse_ng_creates):
        self.logger.clear_log()
        ctx = context.ctx()

        tempdir = tempfile.mkdtemp()

        self._write_files(tempdir, [cluster_json, master_json, worker_json])

        get_configs.return_value = {
            "flavor_id": '2',
            "neutron_management_network": uuidutils.generate_uuid()
        }

        option_values = {"tenant_id": ctx.tenant_id,
                         "directory": tempdir,
                         "norecurse": None,
                         "plugin_name": None,
                         "plugin_version": None}
        template_api.set_conf(Config(option_values))

        add_clts.return_value = True

        template_api.do_update()
        self.assertEqual(1, reverse_ng_creates.call_count)
        self.assertEqual(1, reverse_ng_updates.call_count)

        clts = self.api.cluster_template_get_all(ctx)
        self.assertEqual([], clts)

        msg = ("Skipping processing for {dir}, "
               "error processing cluster templates".format(dir=tempdir))
        self.assertIn(msg, self.logger.warnings)
