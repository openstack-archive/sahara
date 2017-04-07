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


from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.api import v10 as api
import sahara.service.validations.base as b
from sahara.service.validations import shares


def check_node_group_template_create(data, **kwargs):
    plugin_version = 'hadoop_version'
    if data.get('plugin_version'):
        plugin_version = 'plugin_version'

    b.check_node_group_template_unique_name(data['name'])
    b.check_plugin_name_exists(data['plugin_name'])
    b.check_plugin_supports_version(data['plugin_name'],
                                    data[plugin_version])
    b.check_node_group_basic_fields(data['plugin_name'],
                                    data[plugin_version], data)
    if data.get('image_id'):
        b.check_image_registered(data['image_id'])
        b.check_required_image_tags(data['plugin_name'],
                                    data[plugin_version],
                                    data['image_id'])
    if data.get('shares'):
        shares.check_shares(data['shares'])


def check_node_group_template_usage(node_group_template_id, **kwargs):
    cluster_users = []
    template_users = []

    for cluster in api.get_clusters():
        if (node_group_template_id in
            [node_group.node_group_template_id
             for node_group in cluster.node_groups]):
            cluster_users += [cluster.name]

    for cluster_template in api.get_cluster_templates():
        if (node_group_template_id in
            [node_group.node_group_template_id
             for node_group in cluster_template.node_groups]):
            template_users += [cluster_template.name]

    if cluster_users or template_users:
        raise ex.InvalidReferenceException(
            _("Node group template %(template)s is in use by "
              "cluster templates: %(users)s; and clusters: %(clusters)s") %
            {'template': node_group_template_id,
             'users': template_users and ', '.join(template_users) or 'N/A',
             'clusters': cluster_users and ', '.join(cluster_users) or 'N/A'})


def check_node_group_template_update(node_group_template_id, data, **kwargs):
    plugin_version = 'hadoop_version'
    if data.get('plugin_version'):
        plugin_version = 'plugin_version'

    if data.get('plugin_name') and not data.get(plugin_version):
        raise ex.InvalidReferenceException(
            _("You must specify a %s value "
              "for your plugin_name") % plugin_version)

    if data.get('plugin_name'):
        plugin = data.get('plugin_name')
        version = data.get(plugin_version)
        b.check_plugin_name_exists(plugin)
        b.check_plugin_supports_version(plugin, version)
    else:
        ngt = api.get_node_group_template(node_group_template_id)
        plugin = ngt.plugin_name
        if data.get(plugin_version):
            version = data.get(plugin_version)
            b.check_plugin_supports_version(plugin, version)
        else:
            version = ngt.hadoop_version

    if data.get('image_id'):
        b.check_image_registered(data['image_id'])
        b.check_required_image_tags(plugin,
                                    version,
                                    data['image_id'])

    b.check_node_group_basic_fields(plugin, version, data)

    if data.get('shares'):
        shares.check_shares(data['shares'])
