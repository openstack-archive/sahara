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
from savanna.db import models as m
from savanna.db import storage as s
from savanna.openstack.common import excutils
from savanna.openstack.common import log as logging
from savanna.openstack.common import uuidutils
from savanna.plugins import base as plugin_base
from savanna.plugins import provisioning
from savanna.service import instances as i
from savanna.utils.openstack import nova

LOG = logging.getLogger(__name__)


## Cluster ops

get_clusters = s.get_clusters
get_cluster = s.get_cluster


def scale_cluster(cluster_id, data):
    cluster = get_cluster(id=cluster_id)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    existing_node_groups = data.get('resize_node_groups', [])
    additional_node_groups = data.get('add_node_groups', [])

    #the next map is the main object we will work with
    #to_be_enlarged : {node_group_name: desired_amount_of_instances}
    to_be_enlarged = {}
    for ng in existing_node_groups:
        to_be_enlarged.update({ng['name']: ng['count']})

    additional = construct_ngs_for_scaling(additional_node_groups)

    try:
        cluster.status = 'Validating'
        context.model_save(cluster)
        _validate_cluster(cluster, plugin, additional)
        plugin.validate_scaling(cluster, to_be_enlarged, additional)
    except Exception:
        with excutils.save_and_reraise_exception():
            cluster.status = 'Active'
            context.model_save(cluster)

    # If we are here validation is successful.
    # So let's update bd and to_be_enlarged map:
    for add_n_g in additional:
        cluster.node_groups.append(add_n_g)
        to_be_enlarged.update({add_n_g.name: additional[add_n_g]})
    context.model_save(cluster)

    context.spawn(_provision_nodes, cluster_id, to_be_enlarged)
    return cluster


def create_cluster(values):
    cluster = s.create_cluster(values)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)

    # TODO(slukjanov): validate configs and etc.
    _validate(cluster, plugin)

    # validating cluster
    try:
        cluster.status = 'Validating'
        context.model_save(cluster)
        plugin.validate(cluster)
    except Exception:
        with excutils.save_and_reraise_exception():
            cluster.status = 'Error'
            context.model_save(cluster)

    context.spawn(_provision_cluster, cluster.id)

    return cluster


#node_group_names_map = {node_group_name:desired_amount_of_instances}
def _provision_nodes(cluster_id, node_group_names_map):
    cluster = get_cluster(id=cluster_id)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)

    cluster.status = 'Scaling'
    context.model_save(cluster)
    instances = i.scale_cluster(cluster, node_group_names_map)

    cluster.status = 'Configuring'
    context.model_save(cluster)
    plugin.scale_cluster(cluster, instances)

    # cluster is now up and ready
    cluster.status = 'Active'
    context.model_save(cluster)


def _provision_cluster(cluster_id):
    cluster = get_cluster(id=cluster_id)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)

    # updating cluster infra
    cluster.status = 'InfraUpdating'
    context.model_save(cluster)
    plugin.update_infra(cluster)

    # creating instances and configuring them
    i.create_cluster(cluster)

    # configure cluster
    cluster.status = 'Configuring'
    context.model_save(cluster)
    plugin.configure_cluster(cluster)

    # starting prepared and configured cluster
    cluster.status = 'Starting'
    context.model_save(cluster)
    plugin.start_cluster(cluster)

    # cluster is now up and ready
    cluster.status = 'Active'
    context.model_save(cluster)

    return cluster


def terminate_cluster(**args):
    cluster = get_cluster(**args)
    cluster.status = 'Deleting'
    context.model_save(cluster)

    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    plugin.on_terminate_cluster(cluster)

    i.shutdown_cluster(cluster)
    s.terminate_cluster(cluster)


## ClusterTemplate ops

get_cluster_templates = s.get_cluster_templates
get_cluster_template = s.get_cluster_template
create_cluster_template = s.create_cluster_template
terminate_cluster_template = s.terminate_cluster_template


## NodeGroupTemplate ops

get_node_group_templates = s.get_node_group_templates
get_node_group_template = s.get_node_group_template
create_node_group_template = s.create_node_group_template
terminate_node_group_template = s.terminate_node_group_template


## Plugins ops

def get_plugins():
    return plugin_base.PLUGINS.get_plugins(
        base=provisioning.ProvisioningPluginBase)


def get_plugin(plugin_name, version=None):
    plugin = plugin_base.PLUGINS.get_plugin(plugin_name)
    if plugin:
        res = plugin.as_resource()
        if version:
            if version in plugin.get_versions():
                configs = plugin.get_configs(version)
                res._info['configs'] = [c.dict for c in configs]
                processes = plugin.get_node_processes(version)
                res._info['node_processes'] = processes
                required_image_tags = plugin.get_required_image_tags(version)
                res._info['required_image_tags'] = required_image_tags
            else:
                return None
        return res


def convert_to_cluster_template(plugin_name, version, config_file):
    plugin = plugin_base.PLUGINS.get_plugin(plugin_name)
    tenant_id = context.current().tenant_id
    name = uuidutils.generate_uuid()
    ct = m.ClusterTemplate(name, tenant_id, plugin_name, version)
    plugin.convert(ct, config_file)

    return s.persist_cluster_template(ct)


def _validate(cluster, plugin):
    # Validate that user configs are not included in plugin configs set
    pl_confs = _get_plugin_configs(cluster, plugin)
    for ng in cluster.node_groups:
        _validate_node_group(pl_confs, ng)


def _validate_cluster(cluster, plugin, node_groups):
    # Validate that user configs are not included in plugin configs set
    pl_confs = _get_plugin_configs(cluster, plugin)
    for ng in node_groups:
        ng.cluster = cluster
        _validate_node_group(pl_confs, ng)
        ng.cluster = None


def _get_plugin_configs(cluster, plugin):
    pl_confs = {}
    for config in plugin.get_configs(cluster.hadoop_version):
        if pl_confs.get(config.applicable_target):
            pl_confs[config.applicable_target].append(config.name)
        else:
            pl_confs[config.applicable_target] = [config.name]
    return pl_confs


def _validate_node_group(pl_confs, node_group):
    for app_target, configs in node_group.configuration.items():
        if app_target not in pl_confs:
            raise RuntimeError("Plugin doesn't contain applicable "
                               "target '%s'" % app_target)
        for name, values in configs.items():
            if name not in pl_confs[app_target]:
                raise RuntimeError("Plugin's applicable target '%s' "
                                   "doesn't contain config with name '%s'"
                                   % (app_target, name))


def construct_ngs_for_scaling(additional_node_groups):
    additional = {}
    for ng in additional_node_groups:
        tmpl_id = ng['node_group_template_id']
        count = ng['count']
        if tmpl_id:
            tmpl = get_node_group_template(id=tmpl_id)
            node_group = tmpl.to_object(ng, m.NodeGroup)
        else:
            node_group = m.NodeGroup(**ng)
            #need to set 0 because tmpl.to_object overwrote count
        node_group.count = 0
        additional.update({node_group: count})
    return additional

## Image Registry


def get_images(tags):
    return nova.client().images.list_registered(tags)


def get_image(**kwargs):
    if len(kwargs) == 1 and 'id' in kwargs:
        return nova.client().images.get(kwargs['id'])
    else:
        return nova.client().images.find(**kwargs)


def register_image(image_id, username, description=None):
    client = nova.client()
    client.images.set_description(image_id, username, description)
    return client.images.get(image_id)


def unregister_image(image_id):
    client = nova.client()
    client.images.unset_description(image_id)
    return client.images.get(image_id)


def add_image_tags(image_id, tags):
    client = nova.client()
    client.images.tag(image_id, tags)
    return client.images.get(image_id)


def remove_image_tags(image_id, tags):
    client = nova.client()
    client.images.untag(image_id, tags)
    return client.images.get(image_id)
