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

import savanna.db.storage as s
from savanna.openstack.common import log as logging
import savanna.plugins.base as plugin_base
from savanna.plugins.provisioning import ProvisioningPluginBase

LOG = logging.getLogger(__name__)


## Cluster ops

get_clusters = s.get_clusters
get_cluster = s.get_cluster


def create_cluster(values):
    # todo initiate cluster creation here :)
    return s.create_cluster(values)


def terminate_cluster(**args):
    # todo initiate cluster termination here :)
    cluster = get_cluster(**args)
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
    return plugin_base.PLUGINS.get_plugins(base=ProvisioningPluginBase)


def get_plugin(plugin_name, version=None):
    plugin = plugin_base.PLUGINS.get_plugin(plugin_name)
    res = plugin.as_resource()
    if version:
        res._info['configs'] = [c.dict for c in plugin.get_configs(version)]
        res._info['node_processes'] = plugin.get_node_processes(version)
    return res
