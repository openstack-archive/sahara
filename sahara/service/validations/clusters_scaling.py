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

import sahara.exceptions as ex
from sahara.i18n import _
import sahara.plugins.base as plugin_base
import sahara.service.api as api
import sahara.service.validations.base as b
import sahara.service.validations.cluster_template_schema as ct_schema


def _build_node_groups_schema():
    schema = copy.deepcopy(ct_schema.CLUSTER_TEMPLATE_SCHEMA)
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
                        "minimum": 0,
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

    cluster_engine = cluster.sahara_info.get(
        'infrastructure_engine') if cluster.sahara_info else None

    engine_type_and_version = api.OPS.get_engine_type_and_version()
    if (not cluster_engine and
            not engine_type_and_version.startswith('direct')):
        raise ex.InvalidReferenceException(
            _("Cluster created before Juno release "
              "can't be scaled with %(engine)s engine") %
            {"engine": engine_type_and_version})

    if (cluster.sahara_info and
            cluster_engine != engine_type_and_version):
        raise ex.InvalidReferenceException(
            _("Cluster created with %(old_engine)s infrastructure engine "
              "can't be scaled with %(new_engine)s engine") %
            {"old_engine": cluster.sahara_info.get('infrastructure_engine'),
             "new_engine": engine_type_and_version})

    if not (plugin_base.PLUGINS.is_plugin_implements(cluster.plugin_name,
                                                     'scale_cluster') and (
            plugin_base.PLUGINS.is_plugin_implements(cluster.plugin_name,
                                                     'decommission_nodes'))):
        raise ex.InvalidReferenceException(
            _("Requested plugin '%s' doesn't support cluster scaling feature")
            % cluster.plugin_name)

    if cluster.status != 'Active':
        raise ex.InvalidReferenceException(
            _("Cluster cannot be scaled not in 'Active' status. "
              "Cluster status: %s") % cluster.status)

    if data.get("resize_node_groups"):
        b.check_resize(cluster, data['resize_node_groups'])

    if data.get("add_node_groups"):
        b.check_add_node_groups(cluster, data['add_node_groups'])
        b.check_network_config(data['add_node_groups'],
                               cluster.has_proxy_gateway())
        b.check_cluster_hostnames_lengths(cluster.name,
                                          data['add_node_groups'])
