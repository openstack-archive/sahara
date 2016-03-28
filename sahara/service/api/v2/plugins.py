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

from six.moves.urllib import parse as urlparse

from sahara import conductor as c
from sahara import context
from sahara.plugins import base as plugin_base


conductor = c.API


# Plugins ops

def get_plugins():
    return plugin_base.PLUGINS.get_plugins()


def get_plugin(plugin_name, version=None):
    plugin = plugin_base.PLUGINS.get_plugin(plugin_name)
    if plugin:
        res = plugin.as_resource()
        if version:
            if version in plugin.get_versions():
                configs = plugin.get_all_configs(version)
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
