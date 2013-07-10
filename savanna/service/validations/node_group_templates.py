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

import savanna.service.validations.base as b

NODE_GROUP_TEMPLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50,
            "format": "valid_name",
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
        "volumes_mount_prefix": {
            "type": "string",
        },
        "description": {
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
