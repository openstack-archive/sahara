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

from oslo.config import cfg
from oslo.utils import excutils
from oslo_log import log as logging
import six
from six.moves.urllib import parse as urlparse

from sahara import conductor as c
from sahara import context
from sahara.plugins import base as plugin_base
from sahara.plugins import provisioning
from sahara.utils import general as g
from sahara.utils.notification import sender
from sahara.utils.openstack import nova


conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


OPS = None


def setup_service_api(ops):
    global OPS

    OPS = ops


# Cluster ops

def get_clusters(**kwargs):
    return conductor.cluster_get_all(context.ctx(), **kwargs)


def get_cluster(id):
    return conductor.cluster_get(context.ctx(), id)


def scale_cluster(id, data):
    ctx = context.ctx()

    cluster = conductor.cluster_get(ctx, id)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    existing_node_groups = data.get('resize_node_groups', [])
    additional_node_groups = data.get('add_node_groups', [])

    # the next map is the main object we will work with
    # to_be_enlarged : {node_group_id: desired_amount_of_instances}
    to_be_enlarged = {}
    for ng in existing_node_groups:
        ng_id = g.find(cluster.node_groups, name=ng['name'])['id']
        to_be_enlarged.update({ng_id: ng['count']})

    additional = construct_ngs_for_scaling(cluster, additional_node_groups)
    cluster = conductor.cluster_get(ctx, cluster)

    try:
        cluster = g.change_cluster_status(cluster, "Validating")

        plugin.validate_scaling(cluster, to_be_enlarged, additional)
    except Exception:
        with excutils.save_and_reraise_exception():
            g.clean_cluster_from_empty_ng(cluster)
            g.change_cluster_status(cluster, "Active")

    # If we are here validation is successful.
    # So let's update to_be_enlarged map:
    to_be_enlarged.update(additional)

    for node_group in cluster.node_groups:
        if node_group.id not in to_be_enlarged:
            to_be_enlarged[node_group.id] = node_group.count

    OPS.provision_scaled_cluster(id, to_be_enlarged)
    return cluster


def create_cluster(values):
    ctx = context.ctx()
    cluster = conductor.cluster_create(ctx, values)
    sender.notify(ctx, cluster.id, cluster.name, "New",
                  "create")
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)

    # validating cluster
    try:
        cluster = g.change_cluster_status(cluster, "Validating")
        plugin.validate(cluster)
    except Exception as e:
        with excutils.save_and_reraise_exception():
            g.change_cluster_status(cluster, "Error",
                                    status_description=six.text_type(e))

    OPS.provision_cluster(cluster.id)

    return cluster


def terminate_cluster(id):
    cluster = g.change_cluster_status(id, "Deleting")

    OPS.terminate_cluster(id)
    sender.notify(context.ctx(), cluster.id, cluster.name, cluster.status,
                  "delete")

# ClusterTemplate ops


def get_cluster_templates(**kwargs):
    return conductor.cluster_template_get_all(context.ctx(), **kwargs)


def get_cluster_template(id):
    return conductor.cluster_template_get(context.ctx(), id)


def create_cluster_template(values):
    return conductor.cluster_template_create(context.ctx(), values)


def terminate_cluster_template(id):
    return conductor.cluster_template_destroy(context.ctx(), id)


# NodeGroupTemplate ops

def get_node_group_templates(**kwargs):
    return conductor.node_group_template_get_all(context.ctx(), **kwargs)


def get_node_group_template(id):
    return conductor.node_group_template_get(context.ctx(), id)


def create_node_group_template(values):
    return conductor.node_group_template_create(context.ctx(), values)


def terminate_node_group_template(id):
    return conductor.node_group_template_destroy(context.ctx(), id)


# Plugins ops

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


def convert_to_cluster_template(plugin_name, version, template_name,
                                config_file):
    plugin = plugin_base.PLUGINS.get_plugin(plugin_name)
    return plugin.convert(config_file, plugin_name, version,
                          urlparse.unquote(template_name),
                          conductor.cluster_template_create)


def construct_ngs_for_scaling(cluster, additional_node_groups):
    ctx = context.ctx()
    additional = {}
    for ng in additional_node_groups:
        count = ng['count']
        ng['count'] = 0
        ng_id = conductor.node_group_add(ctx, cluster, ng)
        additional.update({ng_id: count})
    return additional

# Image Registry


def get_images(name, tags):
    return nova.client().images.list_registered(name, tags)


def get_image(**kwargs):
    if len(kwargs) == 1 and 'id' in kwargs:
        return nova.client().images.get(kwargs['id'])
    else:
        return nova.client().images.find(**kwargs)


def get_registered_image(id):
    return nova.client().images.get_registered_image(id)


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
