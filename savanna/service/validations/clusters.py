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

import savanna.service.validations.base as b
import savanna.service.validations.cluster_templates as cl_tmpl


def _build_cluster_schema():
    cluster_schema = copy.deepcopy(cl_tmpl.CLUSTER_TEMPLATE_SCHEMA)
    cluster_schema['properties']['name']['format'] = "hostname"
    cluster_schema['properties'].update({
        "user_keypair_id": {
            "type": "string",
            "format": "valid_name",
        },
        "cluster_template_id": {
            "type": "string",
            "format": "uuid",
        }})
    return cluster_schema

CLUSTER_SCHEMA = _build_cluster_schema()


def check_cluster_create(data, **kwargs):
    b.check_cluster_unique_name(data['name'])
    b.check_plugin_name_exists(data['plugin_name'])
    b.check_plugin_supports_version(data['plugin_name'],
                                    data['hadoop_version'])
    if data.get('cluster_template_id'):
        b.check_cluster_template_exists(data['cluster_template_id'])

    if data.get('user_keypair_id'):
        b.check_keypair_exists(data['user_keypair_id'])

    if data.get('default_image_id'):
        b.check_image_registered(data['default_image_id'])

    b.check_all_configurations(data)

    if data.get('anti_affinity'):
        b.check_node_processes(data['plugin_name'], data['hadoop_version'],
                               data['anti_affinity'])
