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

import copy

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service import api
import sahara.service.validations.base as b
import sahara.service.validations.node_group_templates as ng_tml


def _build_ng_schema_for_cluster_tmpl():
    cl_tmpl_ng_schema = copy.deepcopy(ng_tml.NODE_GROUP_TEMPLATE_SCHEMA)
    cl_tmpl_ng_schema['properties'].update({"count": {"type": "integer"}})
    cl_tmpl_ng_schema["required"] = ['name', 'flavor_id',
                                     'node_processes', 'count']
    del cl_tmpl_ng_schema['properties']['hadoop_version']
    del cl_tmpl_ng_schema['properties']['plugin_name']
    return cl_tmpl_ng_schema


_cluster_tmpl_ng_schema = _build_ng_schema_for_cluster_tmpl()


def _build_ng_tmpl_schema_for_cluster_template():
    cl_tmpl_ng_tmpl_schema = copy.deepcopy(_cluster_tmpl_ng_schema)
    cl_tmpl_ng_tmpl_schema['properties'].update(
        {
            "node_group_template_id": {
                "type": "string",
                "format": "uuid",
            }
        })
    cl_tmpl_ng_tmpl_schema["required"] = ["node_group_template_id",
                                          "name", "count"]
    return cl_tmpl_ng_tmpl_schema


_cluster_tmpl_ng_tmpl_schema = _build_ng_tmpl_schema_for_cluster_template()

CLUSTER_TEMPLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50,
            "format": "valid_name_hostname",
        },
        "plugin_name": {
            "type": "string",
        },
        "hadoop_version": {
            "type": "string",
        },
        "default_image_id": {
            "type": "string",
            "format": "uuid",
        },
        "cluster_configs": {
            "type": "configs",
        },
        "node_groups": {
            "type": "array",
            "items": {
                "oneOf": [_cluster_tmpl_ng_tmpl_schema,
                          _cluster_tmpl_ng_schema]
            }
        },
        "anti_affinity": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "description": {
            "type": "string",
        },
        "neutron_management_network": {
            "type": "string",
            "format": "uuid"
        },
    },
    "additionalProperties": False,
    "required": [
        "name",
        "plugin_name",
        "hadoop_version",
    ]
}


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
