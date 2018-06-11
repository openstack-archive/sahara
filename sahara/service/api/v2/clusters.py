# Copyright (c) 2016 Red Hat, Inc.
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


conductor = c.API


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
    node_group_instance_map = {}
    for ng in existing_node_groups:
        ng_id = g.find(cluster.node_groups, name=ng['name'])['id']
        to_be_enlarged.update({ng_id: ng['count']})
        if 'instances' in ng:
            node_group_instance_map.update({ng_id: ng['instances']})

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

    api.OPS.provision_scaled_cluster(id, to_be_enlarged,
                                     node_group_instance_map)
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
        cluster = _cluster_create(cluster_dict, plugin).to_wrapped_dict()

        clusters.append(cluster)

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


def terminate_cluster(id, force=False):
    context.set_current_cluster_id(id)
    cluster = c_u.change_cluster_status(id, c_u.CLUSTER_STATUS_DELETING)

    if cluster is None:
        return

    api.OPS.terminate_cluster(id, force)
    sender.status_notify(cluster.id, cluster.name, cluster.status,
                         "delete")


def update_cluster(id, values):
    if "update_keypair" in values:
        if values["update_keypair"]:
            api.OPS.update_keypair(id)
        values.pop("update_keypair")
    if verification_base.update_verification_required(values):
        api.OPS.handle_verification(id, values)
        return conductor.cluster_get(context.ctx(), id)
    return conductor.cluster_update(context.ctx(), id, values)


def construct_ngs_for_scaling(cluster, additional_node_groups):
    ctx = context.ctx()
    additional = {}
    for ng in additional_node_groups:
        count = ng['count']
        ng['count'] = 0
        ng_id = conductor.node_group_add(ctx, cluster, ng)
        additional.update({ng_id: count})
    return additional
