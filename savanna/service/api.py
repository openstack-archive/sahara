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
from savanna.db import storage as s
from savanna.openstack.common import log as logging
from savanna.plugins import base as plugin_base
from savanna.plugins import provisioning
from savanna.service import instances as i

LOG = logging.getLogger(__name__)


## Cluster ops

get_clusters = s.get_clusters
get_cluster = s.get_cluster


def create_cluster(values):
    cluster = s.create_cluster(values)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)

    # TODO(slukjanov): validate configs and etc.

    # validating cluster
    cluster.status = 'Validating'
    context.model_save(cluster)
    plugin.validate(cluster)

    # TODO(slukjanov): run all following commands in background thread

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
    res = plugin.as_resource()
    if version:
        res._info['configs'] = [c.dict for c in plugin.get_configs(version)]
        res._info['node_processes'] = plugin.get_node_processes(version)
    return res
