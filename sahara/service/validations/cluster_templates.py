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
from sahara.service import api
import sahara.service.validations.base as b


def check_cluster_template_create(data, **kwargs):
    b.check_cluster_template_unique_name(data['name'])
    b.check_plugin_name_exists(data['plugin_name'])
    b.check_plugin_supports_version(data['plugin_name'],
                                    data['hadoop_version'])

    if data.get('default_image_id'):
        b.check_image_registered(data['default_image_id'])
        b.check_required_image_tags(data['plugin_name'],
                                    data['hadoop_version'],
                                    data['default_image_id'])

    b.check_all_configurations(data)

    if data.get('anti_affinity'):
        b.check_node_processes(data['plugin_name'], data['hadoop_version'],
                               data['anti_affinity'])

    if data.get('neutron_management_network'):
        b.check_network_exists(data['neutron_management_network'])


def check_cluster_template_usage(cluster_template_id, **kwargs):
    users = []

    for cluster in api.get_clusters():
        if cluster_template_id == cluster.cluster_template_id:
            users.append(cluster.name)

    if users:
        raise ex.InvalidReferenceException(
            _("Cluster template %(id)s in use by %(clusters)s") %
            {'id': cluster_template_id,
             'clusters':  ', '.join(users)})


def check_cluster_template_update(data, **kwargs):
    if data.get('plugin_name'):
        b.check_plugin_name_exists(data['plugin_name'])

    if data.get('plugin_name') and data.get('hadoop_version'):
        b.check_plugin_supports_version(data['plugin_name'],
                                        data['hadoop_version'])
        b.check_all_configurations(data)

        if data.get('default_image_id'):
            b.check_image_registered(data['default_image_id'])
            b.check_required_image_tags(data['plugin_name'],
                                        data['hadoop_version'],
                                        data['default_image_id'])

        if data.get('anti_affinity'):
            b.check_node_processes(data['plugin_name'], data['hadoop_version'],
                                   data['anti_affinity'])

    if data.get('neutron_management_network'):
        b.check_network_exists(data['neutron_management_network'])
