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

from oslo_config import cfg
from oslo_utils import excutils
import six

from sahara import conductor as c
from sahara import context
from sahara.plugins import base as plugin_base
from sahara.service import api
from sahara.service.health import verification_base
from sahara.service import quotas
from sahara.utils import cluster as c_u
from sahara.utils import general as g
from sahara.utils.notification import sender
from sahara.utils.openstack import base as b
from sahara.utils.openstack import images as sahara_images


conductor = c.API
CONF = cfg.CONF


# Cluster ops

def get_clusters(**kwargs):
    return conductor.cluster_get_all(context.ctx(),
                                     regex_search=True, **kwargs)


def get_cluster(id, show_progress=False):
    return conductor.cluster_get(context.ctx(), id, show_progress)


def scale_cluster(id, data):
    context.set_current_cluster_id(id)
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
    _add_ports_for_auto_sg(ctx, cluster, plugin)

    try:
        cluster = c_u.change_cluster_status(
            cluster, c_u.CLUSTER_STATUS_VALIDATING)
        quotas.check_scaling(cluster, to_be_enlarged, additional)
        plugin.recommend_configs(cluster, scaling=True)
        plugin.validate_scaling(cluster, to_be_enlarged, additional)
    except Exception as e:
        with excutils.save_and_reraise_exception():
            c_u.clean_cluster_from_empty_ng(cluster)
            c_u.change_cluster_status(
                cluster, c_u.CLUSTER_STATUS_ACTIVE, six.text_type(e))

    # If we are here validation is successful.
    # So let's update to_be_enlarged map:
    to_be_enlarged.update(additional)

    for node_group in cluster.node_groups:
        if node_group.id not in to_be_enlarged:
            to_be_enlarged[node_group.id] = node_group.count

    api.OPS.provision_scaled_cluster(id, to_be_enlarged)
    return cluster


def create_cluster(values):
    plugin = plugin_base.PLUGINS.get_plugin(values['plugin_name'])
    return _cluster_create(values, plugin)


def create_multiple_clusters(values):
    num_of_clusters = values['count']
    clusters = []
    plugin = plugin_base.PLUGINS.get_plugin(values['plugin_name'])
    for counter in range(num_of_clusters):
        cluster_dict = values.copy()
        cluster_name = cluster_dict['name']
        cluster_dict['name'] = get_multiple_cluster_name(num_of_clusters,
                                                         cluster_name,
                                                         counter + 1)
        cluster = _cluster_create(cluster_dict, plugin)

        clusters.append(cluster.id)

    clusters_dict = {'clusters': clusters}
    return clusters_dict


def _cluster_create(values, plugin):
    ctx = context.ctx()
    cluster = conductor.cluster_create(ctx, values)
    context.set_current_cluster_id(cluster.id)
    sender.status_notify(cluster.id, cluster.name, "New",
                         "create")
    _add_ports_for_auto_sg(ctx, cluster, plugin)

    # validating cluster
    try:
        plugin.recommend_configs(cluster)
        cluster = c_u.change_cluster_status(
            cluster, c_u.CLUSTER_STATUS_VALIDATING)
        plugin.validate(cluster)
        quotas.check_cluster(cluster)
    except Exception as e:
        with excutils.save_and_reraise_exception():
            c_u.change_cluster_status(
                cluster, c_u.CLUSTER_STATUS_ERROR, six.text_type(e))

    api.OPS.provision_cluster(cluster.id)

    return cluster


def get_multiple_cluster_name(num_of_clusters, name, counter):
    return "%%s-%%0%dd" % len(str(num_of_clusters)) % (name, counter)


def _add_ports_for_auto_sg(ctx, cluster, plugin):
    for ng in cluster.node_groups:
        if ng.auto_security_group:
            ports = {'open_ports': plugin.get_open_ports(ng)}
            conductor.node_group_update(ctx, ng, ports)


def terminate_cluster(id):
    context.set_current_cluster_id(id)
    cluster = c_u.change_cluster_status(id, c_u.CLUSTER_STATUS_DELETING)

    if cluster is None:
        return

    api.OPS.terminate_cluster(id)
    sender.status_notify(cluster.id, cluster.name, cluster.status,
                         "delete")


def update_cluster(id, values):
    if verification_base.update_verification_required(values):
        api.OPS.handle_verification(id, values)
        return conductor.cluster_get(context.ctx(), id)
    return conductor.cluster_update(context.ctx(), id, values)


# ClusterTemplate ops

def get_cluster_templates(**kwargs):
    return conductor.cluster_template_get_all(context.ctx(),
                                              regex_search=True, **kwargs)


def get_cluster_template(id):
    return conductor.cluster_template_get(context.ctx(), id)


def create_cluster_template(values):
    return conductor.cluster_template_create(context.ctx(), values)


def terminate_cluster_template(id):
    return conductor.cluster_template_destroy(context.ctx(), id)


def update_cluster_template(id, values):
    return conductor.cluster_template_update(context.ctx(), id, values)


# NodeGroupTemplate ops

def get_node_group_templates(**kwargs):
    return conductor.node_group_template_get_all(context.ctx(),
                                                 regex_search=True, **kwargs)


def get_node_group_template(id):
    return conductor.node_group_template_get(context.ctx(), id)


def create_node_group_template(values):
    return conductor.node_group_template_create(context.ctx(), values)


def terminate_node_group_template(id):
    return conductor.node_group_template_destroy(context.ctx(), id)


def update_node_group_template(id, values):
    return conductor.node_group_template_update(context.ctx(), id, values)


def export_node_group_template(id):
    return conductor.node_group_template_get(context.ctx(), id)


# Plugins ops

def get_plugins():
    return plugin_base.PLUGINS.get_plugins(serialized=True)


def get_plugin(plugin_name, version=None):
    return plugin_base.PLUGINS.serialize_plugin(plugin_name, version)


def update_plugin(plugin_name, values):
    return plugin_base.PLUGINS.update_plugin(plugin_name, values)


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
    return b.execute_with_retries(
        sahara_images.image_manager().list_registered, name, tags)


def get_image(**kwargs):
    if len(kwargs) == 1 and 'id' in kwargs:
        return b.execute_with_retries(
            sahara_images.image_manager().get, kwargs['id'])
    else:
        return b.execute_with_retries(
            sahara_images.image_manager().find, **kwargs)


def get_registered_image(image_id):
    return b.execute_with_retries(
        sahara_images.image_manager().get_registered_image, image_id)


def register_image(image_id, username, description=None):
    manager = sahara_images.image_manager()
    b.execute_with_retries(
        manager.set_image_info, image_id, username, description)
    return b.execute_with_retries(manager.get, image_id)


def unregister_image(image_id):
    manager = sahara_images.image_manager()
    b.execute_with_retries(manager.unset_image_info, image_id)
    return b.execute_with_retries(manager.get, image_id)


def add_image_tags(image_id, tags):
    manager = sahara_images.image_manager()
    b.execute_with_retries(manager.tag, image_id, tags)
    return b.execute_with_retries(manager.get, image_id)


def remove_image_tags(image_id, tags):
    manager = sahara_images.image_manager()
    b.execute_with_retries(manager.untag, image_id, tags)
    return b.execute_with_retries(manager.get, image_id)
