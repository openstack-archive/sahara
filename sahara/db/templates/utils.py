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

import six

from sahara import conductor


def name_and_id(template):
    return "{name} ({id})".format(name=template["name"],
                                  id=template["id"])


def is_node_group(template):
    # Node group templates and cluster templates have
    # different required fields in validation and neither
    # allows additional fields.  So, the presence of
    # node_processes or flavor_id should suffice to
    # identify a node group template. Check for both
    # to be nice, in case someone made a typo.
    return 'node_processes' in template or 'flavor_id' in template


def substitute_ng_ids(cl, ng_dict):
    '''Substitute node group template ids for node group template names

    If the cluster template contains node group elements with
    node_group_template_id fields that reference node group templates
    by name, substitute the node group template id for the name.
    The name reference is expected to be a string containing a format
    specifier of the form "{name}", for example "{master}"

    :param cl: a cluster template
    :param ng_dict: a dictionary of node group template ids keyed by
                    node group template names
    '''
    for ng in cl["node_groups"]:
        if "node_group_template_id" in ng:
            val = ng["node_group_template_id"].format(**ng_dict)
            ng["node_group_template_id"] = val


def check_basic_fields(template):
    return "plugin_name" in template and (
        "hadoop_version" in template and (
            "name" in template))


def check_plugin_version(template, plugin_versions):
    '''Check that the template  matches the plugin versions list

    Tests whether or not the plugin version indicated by the template
    matches one of the versions specified in plugin_versions

    :param template: A node group or cluster template
    :param plugin_versions: A list of plugin version strings. These
                            values may be regular version strings or may be
                            the name of  the plugin followed by a
                            "." followed by a version string.
    :returns: True if the plugin version specified in the template
              matches a version in plugin_versions or plugin_versions
              is an empty list. Otherwise False
    '''
    def dotted_name(template):
        return template['plugin_name'] + "." + template['hadoop_version']

    version_matches = plugin_versions is None or (
        template['hadoop_version'] in plugin_versions) or (
            dotted_name(template) in plugin_versions)

    return version_matches


def check_plugin_name_and_version(template, plugin_names, plugin_versions):
    '''Check that the template is for one of the specified plugins

    Tests whether or not the plugin name and version indicated by the template
    matches one of the names and one of the versions specified in
    plugin_names and plugin_versions

    :param template: A node group or cluster template
    :param plugin_names: A list of plugin names
    :param plugin_versions: A list of plugin version strings. These
                            values may be regular version strings or may be
                            the name of  the plugin followed by a
                            "." followed by a version string.
    :returns: True if the plugin name specified in the template matches
              a name in plugin_names or plugin_names is an empty list, and if
              the plugin version specified in the template matches a version
              in plugin_versions or plugin_versions is an empty list.
              Otherwise False
    '''
    name_and_version_matches = (plugin_names is None or (
        template['plugin_name'] in plugin_names)) and (
            check_plugin_version(template, plugin_versions))

    return name_and_version_matches


# TODO(tmckay): refactor the service validation code so
# that the node group template usage checks there can be reused
# without incurring unnecessary dependencies
def check_node_group_template_usage(node_group_template_id,
                                    cluster_list, cluster_template_list=None):
    cluster_template_list = cluster_template_list or []
    cluster_users = []
    template_users = []

    for cluster in cluster_list:
        if (node_group_template_id in
            [node_group.node_group_template_id
             for node_group in cluster.node_groups]):
            cluster_users += [cluster.name]

    for cluster_template in cluster_template_list:
        if (node_group_template_id in
            [node_group.node_group_template_id
             for node_group in cluster_template.node_groups]):
            template_users += [cluster_template.name]

    return cluster_users, template_users


# TODO(tmckay): refactor the service validation code so
# that the cluster template usage checks there can be reused
# without incurring unnecessary dependencies
def check_cluster_template_usage(cluster_template_id, cluster_list):
    cluster_users = []
    for cluster in cluster_list:
        if cluster_template_id == cluster.cluster_template_id:
            cluster_users.append(cluster.name)

    return cluster_users


def find_node_group_template_by_name(ctx, name):
    t = conductor.API.node_group_template_get_all(ctx,
                                                  name=name,
                                                  is_default=True)
    if t:
        return t[0]
    return None


def find_cluster_template_by_name(ctx, name):
    t = conductor.API.cluster_template_get_all(ctx,
                                               name=name,
                                               is_default=True)
    if t:
        return t[0]
    return None


def value_diff(current, new_values):
    '''Return the entries in current that would be overwritten by new_values

    Returns the set of entries in current that would be overwritten
    if current.update(new_values) was called.

    :param current: A dictionary whose key values are a superset
                    of the key values in new_values
    :param new_values: A dictionary
    '''
    # Current is an existing template from the db and
    # template is a set of values that has been validated
    # against the JSON schema for the template.
    # Copy items from current if they are present in template.

    # In the case of "node_groups" the conductor does magic
    # to set up template relations and insures that appropriate
    # fields are cleaned (like "updated_at" and "id") so we
    # trust the conductor in that case.

    diff_values = {}
    for k, v in six.iteritems(new_values):
        if k in current and current[k] != v:
            diff_values[k] = copy.deepcopy(current[k])
    return diff_values
