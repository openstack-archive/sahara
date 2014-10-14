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


NODE_GROUP_TEMPLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50,
            "format": "valid_name_hostname",
        },
        "flavor_id": {
            'type': 'flavor',
        },
        "plugin_name": {
            "type": "string",
        },
        "hadoop_version": {
            "type": "string",
        },
        "node_processes": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "minItems": 1
        },
        "image_id": {
            "type": "string",
            "format": "uuid",
        },
        "node_configs": {
            "type": "configs",
        },
        "volumes_per_node": {
            "type": "integer",
            "minimum": 0,
        },
        "volumes_size": {
            "type": "integer",
            "minimum": 1,
        },
        "volume_type": {
            "type": "string"
        },
        "volumes_availability_zone": {
            "type": "string",
        },
        "volume_mount_prefix": {
            "type": "string",
            "format": "posix_path",
        },
        "description": {
            "type": "string",
        },
        "floating_ip_pool": {
            "type": "string",
        },
        "security_groups": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "auto_security_group": {
            "type": "boolean"
        },
        "availability_zone": {
            "type": "string",
        },
    },
    "additionalProperties": False,
    "required": [
        "name",
        "flavor_id",
        "plugin_name",
        "hadoop_version",
        "node_processes",
    ]
}


def check_node_group_template_create(data, **kwargs):
    b.check_node_group_template_unique_name(data['name'])
    b.check_plugin_name_exists(data['plugin_name'])
    b.check_plugin_supports_version(data['plugin_name'],
                                    data['hadoop_version'])
    b.check_node_group_basic_fields(data['plugin_name'],
                                    data['hadoop_version'], data)


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
        raise ex.InvalidException(
            _("Node group template %(template)s is in use by "
              "cluster templates: %(users)s; and clusters: %(clusters)s") %
            {'template': node_group_template_id,
             'users': template_users and ', '.join(template_users) or 'N/A',
             'clusters': cluster_users and ', '.join(cluster_users) or 'N/A'})
