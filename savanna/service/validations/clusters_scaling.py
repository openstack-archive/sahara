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

import savanna.exceptions as ex
import savanna.plugins.base as plugin_base
import savanna.service.api as api
import savanna.service.validations.base as b
import savanna.service.validations.cluster_templates as cl_t


def _build_node_groups_schema():
    schema = copy.deepcopy(cl_t.CLUSTER_TEMPLATE_SCHEMA)
    return schema['properties']['node_groups']


CLUSTER_SCALING_SCHEMA = {
    "type": "object",
    "properties": {
        "resize_node_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                    },
                },
                "additionalProperties": False,
                "required": [
                    "name",
                    "count",
                ]
            },
            "minItems": 1
        },
        "add_node_groups": _build_node_groups_schema(),
    },
    "additionalProperties": False,
    "anyOf": [
        {
            "required": ["resize_node_groups"]
        },
        {
            "required": ["add_node_groups"]
        }
    ]

}


def check_cluster_scaling(data, cluster_id, **kwargs):
    cluster = api.get_cluster(id=cluster_id)
    if not plugin_base.PLUGINS.is_plugin_implements(cluster.plugin_name,
                                                    'scale_cluster'):
        raise ex.InvalidException(
            "Requested plugin '%s' doesn't support cluster scaling feature"
            % cluster.plugin_name)

    if cluster.status != 'Active':
        raise ex.InvalidException("Cluster cannot be scaled not in 'Active' "
                                  "status. Cluster status: " + cluster.status)

    if data.get("resize_node_groups"):
        b.check_resize(cluster, data['resize_node_groups'])

    if data.get("add_node_groups"):
        b.check_add_node_groups(cluster, data['add_node_groups'])
