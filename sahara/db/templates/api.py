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
import os

import jsonschema
from oslo_config import cfg
from oslo_serialization import jsonutils as json
from oslo_utils import uuidutils
import six

from sahara import conductor
from sahara.db.templates import utils as u
from sahara.service.validations import cluster_template_schema as clt
from sahara.service.validations import node_group_template_schema as ngt
from sahara.utils import api_validator


LOG = None
CONF = None


# This is broken out to support testability
def set_logger(log):
    global LOG
    LOG = log


# This is broken out to support testability
def set_conf(conf):
    global CONF
    CONF = conf


ng_validator = api_validator.ApiValidator(ngt.NODE_GROUP_TEMPLATE_SCHEMA)
ct_validator = api_validator.ApiValidator(clt.CLUSTER_TEMPLATE_SCHEMA)

# Options that we allow to be replaced in a node group template
node_group_template_opts = [
    cfg.StrOpt('image_id',
               help='Image id field for a node group template.'),

    cfg.StrOpt('flavor_id',
               help='Flavor id field for a node group template.'),

    cfg.StrOpt('floating_ip_pool',
               help='Floating ip pool field for a node group template.'),
    cfg.BoolOpt('auto_security_group',
                default=False,
                help='Auto security group field for node group template.'),
    cfg.ListOpt('security_groups',
                default=[],
                help='Security group field for node group template.')
]

# Options that we allow to be replaced in a cluster template
cluster_template_opts = [
    cfg.StrOpt('default_image_id',
               help='Default image id field for a cluster template.'),

    cfg.StrOpt('neutron_management_network',
               help='Neutron management network '
               'field for a cluster template.')]

all_template_opts = node_group_template_opts + cluster_template_opts

node_group_template_opt_names = [o.name for o in node_group_template_opts]
cluster_template_opt_names = [o.name for o in cluster_template_opts]


# This is a local exception class that is used to exit routines
# in cases where error information has already been logged.
# It is caught and suppressed everywhere it is used.
class Handled(Exception):
    pass


class Context(object):
    '''Create a pseudo Context object

    Since this tool does not use the REST interface, we
    do not have a request from which to build a Context.
    '''
    def __init__(self, is_admin=False, tenant_id=None):
        self.is_admin = is_admin
        self.tenant_id = tenant_id


def check_usage_of_existing(ctx, ng_templates, cl_templates):
    '''Determine if any of the specified templates are in use

    This method searches for the specified templates by name and
    determines whether or not any existing templates are in use
    by a cluster or cluster template. Returns True if any of
    the templates are in use.

    :param ng_templates: A list of dictionaries. Each dictionary
                         has a "template" entry that represents
                         a node group template.
    :param cl_templates: A list of dictionaries. Each dictionary
                         has a "template" entry that represents
                         a cluster template
    :returns: True if any of the templates are in use, False otherwise
    '''
    error = False
    clusters = conductor.API.cluster_get_all(ctx)

    for ng_info in ng_templates:
        ng = u.find_node_group_template_by_name(ctx,
                                                ng_info["template"]["name"])
        if ng:
            cluster_users, template_users = u.check_node_group_template_usage(
                ng["id"], clusters)

            if cluster_users:
                LOG.warning("Node group template {name} "
                            "in use by clusters {clusters}".format(
                                name=ng["name"], clusters=cluster_users))
            if template_users:
                LOG.warning("Node group template {name} "
                            "in use by cluster templates {templates}".format(
                                name=ng["name"], templates=template_users))

            if cluster_users or template_users:
                LOG.warning("Update of node group template "
                            "{name} is not allowed".format(name=ng["name"]))
                error = True

    for cl_info in cl_templates:
        cl = u.find_cluster_template_by_name(ctx, cl_info["template"]["name"])
        if cl:
            cluster_users = u.check_cluster_template_usage(cl["id"], clusters)

            if cluster_users:
                LOG.warning("Cluster template {name} "
                            "in use by clusters {clusters}".format(
                                name=cl["name"], clusters=cluster_users))

                LOG.warning("Update of cluster template "
                            "{name} is not allowed".format(name=cl["name"]))
                error = True

    return error


def log_skipping_dir(path, reason=""):
    if reason:
        reason = ", " + reason
    LOG.warning("Skipping processing for {dir}{reason}".format(
        dir=path, reason=reason))


def check_cluster_templates_valid(ng_templates, cl_templates):
    # Check that if name references to node group templates
    # are replaced with a uuid value that the cluster template
    # passes JSON validation. We don't have the real uuid yet,
    # but this will allow the validation test.
    if ng_templates:
        dummy_uuid = uuidutils.generate_uuid()
        ng_ids = {ng["template"]["name"]: dummy_uuid for ng in ng_templates}
    else:
        ng_ids = {}

    for cl in cl_templates:
        template = copy.deepcopy(cl["template"])
        u.substitute_ng_ids(template, ng_ids)
        try:
            ct_validator.validate(template)
        except jsonschema.ValidationError as e:
            LOG.warning("Validation for {path} failed, {reason}".format(
                path=cl["path"], reason=e))
            return True
    return False


def add_config_section(section_name, options):
    if section_name and hasattr(CONF, section_name):
        # It's already been added
        return

    if section_name:
        group = cfg.OptGroup(name=section_name)
        CONF.register_group(group)
        CONF.register_opts(options, group)
    else:
        # Add options to the default section
        CONF.register_opts(options)


def add_config_section_for_template(template):
    '''Register a config section based on the template values

    Check to see if the configuration files contain a section
    that corresponds to the template.  If an appropriate section
    can be found, register options for the template so that the
    config values can be read and applied to the template via
    substitution (oslo supports registering groups and options
    at any time, before or after the config files are parsed).

    Corresponding section names may be of the following forms:

    <template_name>, example "hdp-2.0.6-master"
    This is useful when a template naming convention is being used,
    so that the template name is already unambiguous

    <plugin_name>_<hadoop_version>_<template_name>, example "hdp_2.0.6_master"
    This can be used if there is a name collision between templates

    <plugin_name>_<hadoop_version>, example "hdp_2.0.6"
    <plugin_name>, example "hdp"
    DEFAULT

    Sections are tried in the order given above.

    Since the first two section naming forms refer to a specific
    template by name, options are added based on template type.

    However, the other section naming forms may map to node group templates
    or cluster templates, so options for both are added.
    '''
    sections = list(CONF.list_all_sections())

    unique_name = "{name}".format(**template)
    fullname = "{plugin_name}_{hadoop_version}_{name}".format(**template)
    plugin_version = "{plugin_name}_{hadoop_version}".format(**template)
    plugin = "{plugin_name}".format(**template)

    section_name = None
    if unique_name in sections:
        section_name = unique_name
    elif fullname in sections:
        section_name = fullname

    if section_name:
        if u.is_node_group(template):
            opts = node_group_template_opts
        else:
            opts = cluster_template_opts
    else:
        if plugin_version in sections:
            section_name = plugin_version
        elif plugin in sections:
            section_name = plugin
        opts = all_template_opts

    add_config_section(section_name, opts)
    return section_name


def substitute_config_values(configs, template, path):
    if u.is_node_group(template):
        opt_names = node_group_template_opt_names
    else:
        opt_names = cluster_template_opt_names

    for opt, value in six.iteritems(configs):
        if opt in opt_names and opt in template:
            template[opt] = value


def get_configs(section):
    if section is None:
        return dict(CONF)
    return dict(CONF[section])


def get_plugin_name():
    if CONF.command.name == "update" and (
            not CONF.command.plugin_name and (
                hasattr(CONF, "plugins") and CONF.plugins)):
        return CONF.plugins
    return CONF.command.plugin_name


def process_files(dirname, files):

    node_groups = []
    clusters = []
    plugin_name = get_plugin_name()

    try:
        for fname in files:
            if os.path.splitext(fname)[1] == ".json":
                fpath = os.path.join(dirname, fname)
                with open(fpath, 'r') as fp:
                    try:
                        data = fp.read()
                        template = json.loads(data)
                    except ValueError as e:
                        LOG.warning("Error processing {path}, "
                                    "{reason}".format(path=fpath, reason=e))
                        raise Handled("error processing files")

                    # If this file doesn't contain basic fields, skip it.
                    # If we are filtering on plugin and version make
                    # sure the file is one that we want
                    if not u.check_basic_fields(template) or (
                            not u.check_plugin_name_and_version(
                                template,
                                plugin_name,
                                CONF.command.plugin_version)):
                        continue

                    # Look through the sections in CONF and register
                    # options for this template if we find a section
                    # related to the template (ie, plugin, version, name)
                    section = add_config_section_for_template(template)
                    LOG.debug("Using config section {section} "
                              "for {path}".format(section=section, path=fpath))

                    # Attempt to resolve substitutions using the config section
                    substitute_config_values(get_configs(section),
                                             template, fpath)

                    file_entry = {'template': template,
                                  'path': fpath}

                    if u.is_node_group(template):
                        # JSON validator
                        try:
                            ng_validator.validate(template)
                        except jsonschema.ValidationError as e:
                            LOG.warning("Validation for {path} failed, "
                                        "{reason}".format(path=fpath,
                                                          reason=e))
                            raise Handled(
                                "node group template validation failed")
                        node_groups.append(file_entry)
                        LOG.debug("Added {path} to node group "
                                  "template files".format(path=fpath))
                    else:
                        clusters.append(file_entry)
                        LOG.debug("Added {path} to cluster template "
                                  "files".format(path=fpath))

    except Handled as e:
        log_skipping_dir(dirname, str(e))
        node_groups = []
        clusters = []

    except Exception as e:
        log_skipping_dir(dirname,
                         "unhandled exception, {reason}".format(reason=e))
        node_groups = []
        clusters = []

    return node_groups, clusters


def delete_node_group_template(ctx, template, rollback=False):
    rollback_msg = " on rollback" if rollback else ""

    # If we are not deleting something that we just created,
    # do usage checks to ensure that the template is not in
    # use by a cluster or a cluster template
    if not rollback:
        clusters = conductor.API.cluster_get_all(ctx)
        cluster_templates = conductor.API.cluster_template_get_all(ctx)
        cluster_users, template_users = u.check_node_group_template_usage(
            template["id"], clusters, cluster_templates)

        if cluster_users:
            LOG.warning("Node group template {info} "
                        "in use by clusters {clusters}".format(
                            info=u.name_and_id(template),
                            clusters=cluster_users))
        if template_users:
            LOG.warning("Node group template {info} "
                        "in use by cluster templates {templates}".format(
                            info=u.name_and_id(template),
                            templates=template_users))

        if cluster_users or template_users:
            LOG.warning("Deletion of node group template "
                        "{info} failed".format(info=u.name_and_id(template)))
            return

    try:
        conductor.API.node_group_template_destroy(ctx, template["id"],
                                                  ignore_prot_on_def=True)
    except Exception as e:
        LOG.warning("Deletion of node group template {info} "
                    "failed{rollback}, {reason}".format(
                        info=u.name_and_id(template),
                        reason=e,
                        rollback=rollback_msg))
    else:
        LOG.info("Deleted node group template {info}{rollback}".format(
            info=u.name_and_id(template), rollback=rollback_msg))


def reverse_node_group_template_creates(ctx, templates):
    for template in templates:
        delete_node_group_template(ctx, template, rollback=True)


def reverse_node_group_template_updates(ctx, update_info):
    for template, values in update_info:
        # values are the original values that we overwrote in the update
        try:
            conductor.API.node_group_template_update(ctx,
                                                     template["id"], values,
                                                     ignore_prot_on_def=True)
        except Exception as e:
            LOG.warning("Rollback of update for node group "
                        "template {info} failed, {reason}".format(
                            info=u.name_and_id(template),
                            reason=e))
        else:
            LOG.info("Rolled back update for node group "
                     "template {info}".format(info=u.name_and_id(template)))


def add_node_group_templates(ctx, node_groups):

    error = False
    ng_info = {"ids": {},
               "created": [],
               "updated": []}

    def do_reversals(ng_info):
        reverse_node_group_template_updates(ctx, ng_info["updated"])
        reverse_node_group_template_creates(ctx, ng_info["created"])
        return {}, True

    try:
        for ng in node_groups:
            template = ng['template']
            current = u.find_node_group_template_by_name(ctx, template['name'])
            if current:

                # Track what we see in the current template that is different
                # from our update values. Save it for possible rollback.
                # Note, this is not perfect because it does not recurse through
                # nested structures to get an exact diff, but it ensures that
                # we track only fields that are valid in the JSON schema
                updated_fields = u.value_diff(current.to_dict(), template)

                # Always attempt to update.  Since the template value is a
                # combination of JSON and config values, there is no useful
                # timestamp we can use to skip an update.
                # If sqlalchemy determines no change in fields, it will not
                # mark it as updated.
                try:
                    template = conductor.API.node_group_template_update(
                        ctx, current['id'], template, ignore_prot_on_def=True)
                except Exception as e:
                    LOG.warning("Update of node group template {info} "
                                "failed, {reason}".format(
                                    info=u.name_and_id(current),
                                    reason=e))
                    raise Handled()

                if template['updated_at'] != current['updated_at']:
                    ng_info["updated"].append((template, updated_fields))
                    LOG.info("Updated node group template {info} "
                             "from {path}".format(info=u.name_and_id(template),
                                                  path=ng["path"]))
                else:
                    LOG.debug("No change to node group template {info} "
                              "from {path}".format(
                                  info=u.name_and_id(current),
                                  path=ng['path']))
            else:
                template['is_default'] = True
                try:
                    template = conductor.API.node_group_template_create(
                        ctx, template)
                except Exception as e:
                    LOG.warning("Creation of node group template "
                                "from {path} failed, {reason}".format(
                                    path=ng['path'], reason=e))
                    raise Handled()

                ng_info["created"].append(template)
                LOG.info("Created node group template {info} "
                         "from {path}".format(info=u.name_and_id(template),
                                              path=ng["path"]))

            # For the purposes of substitution we need a dict of id by name
            ng_info["ids"][template['name']] = template['id']

    except Handled:
        ng_info, error = do_reversals(ng_info)

    except Exception as e:
        LOG.warning("Unhandled exception while processing "
                    "node group templates, {reason}".format(reason=e))
        ng_info, error = do_reversals(ng_info)

    return ng_info, error


def delete_cluster_template(ctx, template, rollback=False):
    rollback_msg = " on rollback" if rollback else ""

    # If we are not deleting something that we just created,
    # do usage checks to ensure that the template is not in
    # use by a cluster
    if not rollback:
        clusters = conductor.API.cluster_get_all(ctx)
        cluster_users = u.check_cluster_template_usage(template["id"],
                                                       clusters)

        if cluster_users:
            LOG.warning("Cluster template {info} "
                        "in use by clusters {clusters}".format(
                            info=u.name_and_id(template),
                            clusters=cluster_users))

            LOG.warning("Deletion of cluster template "
                        "{info} failed".format(info=u.name_and_id(template)))
            return

    try:
        conductor.API.cluster_template_destroy(ctx, template["id"],
                                               ignore_prot_on_def=True)
    except Exception as e:
        LOG.warning("Deletion of cluster template {info} failed{rollback}"
                    ", {reason}".format(info=u.name_and_id(template),
                                        reason=e,
                                        rollback=rollback_msg))
    else:
        LOG.info("Deleted cluster template {info}{rollback}".format(
            info=u.name_and_id(template), rollback=rollback_msg))


def reverse_cluster_template_creates(ctx, templates):
    for template in templates:
        delete_cluster_template(ctx, template, rollback=True)


def reverse_cluster_template_updates(ctx, update_info):
    for template, values in update_info:
        # values are the original values that we overwrote in the update
        try:
            conductor.API.cluster_template_update(ctx,
                                                  template["id"], values,
                                                  ignore_prot_on_def=True)
        except Exception as e:
            LOG.warning("Rollback of update for cluster "
                        "template {info} failed, {reason}".format(
                            info=u.name_and_id(template),
                            reason=e))
        else:
            LOG.info("Rolled back update for cluster "
                     "template {info}".format(info=u.name_and_id(template)))


def add_cluster_templates(ctx, clusters, ng_dict):
    '''Add cluster templates to the database.

    The value of any node_group_template_id fields in cluster
    templates which reference a node group template in ng_dict by name
    will be changed to the id of the node group template.

    If there is an error in creating or updating a template, any templates
    that have already been created will be delete and any updates will
    be reversed.

    :param clusters: a list of dictionaries. Each dictionary
                     has a "template" entry holding the cluster template
                     and a "path" entry holding the path of the file
                     from which the template was read.
    :param ng_dict: a dictionary of node group template ids keyed
                    by node group template names
    '''

    error = False
    created = []
    updated = []

    def do_reversals(created, updated):
        reverse_cluster_template_updates(ctx, updated)
        reverse_cluster_template_creates(ctx, created)
        return True

    try:
        for cl in clusters:
            template = cl['template']

            # Fix up node_group_template_id fields
            u.substitute_ng_ids(template, ng_dict)

            # Name + tenant_id is unique, so search by name
            current = u.find_cluster_template_by_name(ctx, template['name'])
            if current:

                # Track what we see in the current template that is different
                # from our update values. Save it for possible rollback.
                # Note, this is not perfect because it does not recurse through
                # nested structures to get an exact diff, but it ensures that
                # we track only fields that are valid in the JSON schema
                updated_fields = u.value_diff(current.to_dict(), template)

                # Always attempt to update.  Since the template value is a
                # combination of JSON and config values, there is no useful
                # timestamp we can use to skip an update.
                # If sqlalchemy determines no change in fields, it will not
                # mark it as updated.

                # TODO(tmckay): why when I change the count in an
                # entry in node_groups does it not count as an update?
                # Probably a bug
                try:
                    template = conductor.API.cluster_template_update(
                        ctx, current['id'], template, ignore_prot_on_def=True)
                except Exception as e:
                    LOG.warning("Update of cluster template {info} "
                                "failed, {reason}".format(
                                    info=u.name_and_id(current), reason=e))
                    raise Handled()

                if template['updated_at'] != current['updated_at']:
                    updated.append((template, updated_fields))
                    LOG.info("Updated cluster template {info} "
                             "from {path}".format(info=u.name_and_id(template),
                                                  path=cl['path']))
                else:
                    LOG.debug("No change to cluster template {info} "
                              "from {path}".format(info=u.name_and_id(current),
                                                   path=cl["path"]))
            else:
                template["is_default"] = True
                try:
                    template = conductor.API.cluster_template_create(ctx,
                                                                     template)
                except Exception as e:
                    LOG.warning("Creation of cluster template "
                                "from {path} failed, {reason}".format(
                                    path=cl['path'],
                                    reason=e))
                    raise Handled()

                created.append(template)
                LOG.info("Created cluster template {info} "
                         "from {path}".format(info=u.name_and_id(template),
                                              path=cl['path']))

    except Handled:
        error = do_reversals(created, updated)

    except Exception as e:
        LOG.warning("Unhandled exception while processing "
                    "cluster templates, {reason}".format(reason=e))
        error = do_reversals(created, updated)

    return error


def do_update():
    '''Create or update default templates for the specified tenant.

    Looks for '.json' files beginning at the specified starting
    directory (--directory CLI option) and descending
    through subdirectories by default.

    The .json files represent cluster templates or node group
    templates. All '.json' files at the same directory level are treated
    as a set. Cluster templates may reference node group templates
    in the same set.

    If an error occurs in processing a set, skip it and continue.

    If creation of cluster templates fails, any node group templates
    in the set that were already created will be deleted.
    '''

    ctx = Context(tenant_id=CONF.command.tenant_id)
    start_dir = os.path.abspath(CONF.command.directory)

    for root, dirs, files in os.walk(start_dir):

        # Find all the template files and identify them as node_group
        # or cluster templates. If there is an exception in
        # processing the set, return empty lists.
        node_groups, clusters = process_files(root, files)

        # Now that we know what the valid node group templates are,
        # we can validate the cluster templates as well.
        if check_cluster_templates_valid(node_groups, clusters):
            log_skipping_dir(root, "error processing cluster templates")

        # If there are existing default templates that match the names
        # in the template files, do usage checks here to detect update
        # failures early (we can't update a template in use)
        elif check_usage_of_existing(ctx, node_groups, clusters):
            log_skipping_dir(root, "templates in use")
        else:
            ng_info, error = add_node_group_templates(ctx, node_groups)
            if error:
                log_skipping_dir(root, "error processing node group templates")

            elif add_cluster_templates(ctx, clusters, ng_info["ids"]):
                log_skipping_dir(root, "error processing cluster templates")

                # Cluster templates failed so remove the node group templates
                reverse_node_group_template_updates(ctx, ng_info["updated"])
                reverse_node_group_template_creates(ctx, ng_info["created"])

        if CONF.command.norecurse:
            break


def do_delete():
    '''Delete default templates in the specified tenant

    Deletion uses the --plugin-name and --plugin-version options
    as filters.

    Only templates with 'is_default=True' will be deleted.
    '''

    ctx = Context(tenant_id=CONF.command.tenant_id)

    for plugin in get_plugin_name():

        kwargs = {'is_default': True}
        kwargs['plugin_name'] = plugin

        # Delete cluster templates first for the sake of usage checks
        lst = conductor.API.cluster_template_get_all(ctx, **kwargs)
        for l in lst:
            if not u.check_plugin_version(l, CONF.command.plugin_version):
                continue
            delete_cluster_template(ctx, l)

        lst = conductor.API.node_group_template_get_all(ctx, **kwargs)
        for l in lst:
            if not u.check_plugin_version(l, CONF.command.plugin_version):
                continue
            delete_node_group_template(ctx, l)


def do_node_group_template_delete():
    ctx = Context(tenant_id=CONF.command.tenant_id)

    template_name = CONF.command.template_name
    t = u.find_node_group_template_by_name(ctx, template_name)
    if t:
        delete_node_group_template(ctx, t)
    else:
        LOG.warning("Deletion of node group template {name} failed, "
                    "no such template".format(name=template_name))


def do_node_group_template_delete_by_id():
    ctx = Context(is_admin=True)

    # Make sure it's a default
    t = conductor.API.node_group_template_get(ctx, CONF.command.id)
    if t:
        if t["is_default"]:
            delete_node_group_template(ctx, t)
        else:
            LOG.warning("Deletion of node group template {info} skipped, "
                        "not a default template".format(
                            info=u.name_and_id(t)))
    else:
        LOG.warning("Deletion of node group template {id} failed, "
                    "no such template".format(id=CONF.command.id))


def do_cluster_template_delete():
    ctx = Context(tenant_id=CONF.command.tenant_id)

    template_name = CONF.command.template_name
    t = u.find_cluster_template_by_name(ctx, template_name)
    if t:
        delete_cluster_template(ctx, t)
    else:
        LOG.warning("Deletion of cluster template {name} failed, "
                    "no such template".format(name=template_name))


def do_cluster_template_delete_by_id():
    ctx = Context(is_admin=True)

    # Make sure it's a default
    t = conductor.API.cluster_template_get(ctx, CONF.command.id)
    if t:
        if t["is_default"]:
            delete_cluster_template(ctx, t)
        else:
            LOG.warning("Deletion of cluster template {info} skipped, "
                        "not a default template".format(
                            info=u.name_and_id(t)))
    else:
        LOG.warning("Deletion of cluster template {id} failed, "
                    "no such template".format(id=CONF.command.id))
