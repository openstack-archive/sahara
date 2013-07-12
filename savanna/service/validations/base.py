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

import novaclient.exceptions as nova_ex

import savanna.exceptions as ex
import savanna.plugins.base as plugin_base
import savanna.service.api as api
import savanna.utils.openstack.nova as nova


def _get_plugin_configs(plugin_name, hadoop_version, scope=None):
    pl_confs = {}
    for config in plugin_base.PLUGINS.get_plugin(
            plugin_name).get_configs(hadoop_version):
        if pl_confs.get(config.applicable_target):
            pl_confs[config.applicable_target].append(config.name)
        else:
            pl_confs[config.applicable_target] = [config.name]
    return pl_confs


## Common validation checks

def check_plugin_name_exists(name):
    if name not in [p.name for p in api.get_plugins()]:
        raise ex.InvalidException("Savanna doesn't contain plugin with name "
                                  "'%s'" % name)


def check_plugin_supports_version(p_name, version):
    if version not in plugin_base.PLUGINS.get_plugin(p_name).get_versions():
        raise ex.InvalidException("Requested plugin '%s' doesn't support"
                                  " version '%s'" % (p_name, version))


def check_image_registered(image_id):
    if image_id not in [i.id for i in nova.client().images.list_registered()]:
        raise ex.InvalidException("Requested image '%s' is not registered"
                                  % image_id)


def check_node_group_configs(plugin_name, hadoop_version, ng_configs,
                             plugin_configs=None):
    # TODO(aignatov): Should have scope and config type validations
    pl_confs = plugin_configs or _get_plugin_configs(plugin_name,
                                                     hadoop_version)
    for app_target, configs in ng_configs.items():
        if app_target not in pl_confs:
            raise ex.InvalidException("Plugin doesn't contain applicable "
                                      "target '%s'" % app_target)
        for name, values in configs.items():
            if name not in pl_confs[app_target]:
                raise ex.InvalidException("Plugin's applicable target '%s' "
                                          "doesn't contain config with name "
                                          "'%s'" % (app_target, name))


def check_all_configurations(data):
    pl_confs = _get_plugin_configs(data['plugin_name'], data['hadoop_version'])

    if data.get('cluster_configs'):
        check_node_group_configs(data['plugin_name'], data['hadoop_version'],
                                 data['cluster_configs'],
                                 plugin_configs=pl_confs)

    if data.get('node_groups'):
        for ng in data['node_groups']:
            check_node_group_basic_fields(data['plugin_name'],
                                          data['hadoop_version'],
                                          ng, pl_confs)

## NodeGroup related checks


def check_node_group_basic_fields(plugin_name, hadoop_version, ng,
                                  plugin_configs=None):

    if ng.get('node_group_template_id'):
        check_node_group_template_exists(ng['node_group_template_id'])

    if ng.get('node_configs'):
        check_node_group_configs(plugin_name, hadoop_version,
                                 ng['node_configs'], plugin_configs)
    if ng.get('flavor_id'):
        check_flavor_exists(ng['flavor_id'])

    if ng.get('node_processes'):
        check_node_processes(plugin_name, hadoop_version, ng['node_processes'])

    if ng.get('image_id'):
        check_image_registered(ng['image_id'])


def check_flavor_exists(flavor_id):
    try:
        nova.client().flavors.get(flavor_id)
    except nova_ex.NotFound:
        raise ex.InvalidException("Requested flavor '%s' not found"
                                  % flavor_id)


def check_node_processes(plugin_name, version, node_processes):
    if len(set(node_processes)) != len(node_processes):
        raise ex.InvalidException("Duplicates in node processes "
                                  "have been detected")
    plugin_procesess = []
    for process in plugin_base.PLUGINS.get_plugin(
            plugin_name).get_node_processes(version).values():
        plugin_procesess += process

    if not set(node_processes).issubset(set(plugin_procesess)):
        raise ex.InvalidException("Plugin supports the following "
                                  "node procesess: %s" % plugin_procesess)


def check_duplicates_node_groups_names(node_groups):
    ng_names = [ng['name'] for ng in node_groups]
    if len(set(ng_names)) < len(node_groups):
        raise ex.InvalidException("Duplicates in node group names "
                                  "are detected")


## Cluster creation related checks

def check_cluster_unique_name(name):
    if name in [cluster.name for cluster in api.get_clusters()]:
        raise ex.NameAlreadyExistsException("Cluster with name '%s' already"
                                            " exists" % name)


def check_keypair_exists(keypair):
    try:
        nova.client().keypairs.get(keypair)
    except nova_ex.NotFound:
        raise ex.InvalidException("Requested keypair '%s' not found" % keypair)


## Cluster templates related checks

def check_cluster_template_unique_name(name):
    if name in [t.name for t in api.get_cluster_templates()]:
        raise ex.NameAlreadyExistsException("Cluster template with name '%s'"
                                            " already exists" % name)


def check_cluster_template_exists(cluster_template_id):
    if not api.get_cluster_templates(id=cluster_template_id):
        raise ex.InvalidException("Cluster template with id '%s'"
                                  " doesn't exist" % cluster_template_id)


## NodeGroup templates related checks

def check_node_group_template_unique_name(name):
    if name in [t.name for t in api.get_node_group_templates()]:
        raise ex.NameAlreadyExistsException("NodeGroup template with name '%s'"
                                            " already exists" % name)


def check_node_group_template_exists(ng_tmpl_id):
    if not api.get_node_group_templates(id=ng_tmpl_id):
        raise ex.InvalidException("NodeGroup template with id '%s'"
                                  " doesn't exist" % ng_tmpl_id)


## Cluster scaling

def check_resize(cluster, r_node_groups):
    cluster_ng_names = [ng.name for ng in cluster.node_groups]

    check_duplicates_node_groups_names(r_node_groups)

    for ng in r_node_groups:
        if ng['name'] not in cluster_ng_names:
            raise ex.InvalidException("Cluster doesn't contain node group "
                                      "with name '%s'" % ng['name'])


def check_add_node_groups(cluster, add_node_groups):
    cluster_ng_names = [ng.name for ng in cluster.node_groups]

    check_duplicates_node_groups_names(add_node_groups)

    pl_confs = _get_plugin_configs(cluster.plugin_name, cluster.hadoop_version)

    for ng in add_node_groups:
        if ng['name'] in cluster_ng_names:
            raise ex.InvalidException("Can't add new nodegroup. Cluster "
                                      "already has nodegroup with name '%s'"
                                      % ng['name'])

        check_node_group_basic_fields(cluster.plugin_name,
                                      cluster.hadoop_version, ng, pl_confs)
