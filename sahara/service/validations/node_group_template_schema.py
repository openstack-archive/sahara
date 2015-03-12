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
        "is_proxy_gateway": {
            "type": "boolean"
        },
        "volume_local_to_instance": {
            "type": "boolean"
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

# For an update we do not require any fields but we want the given
# fields to be validated
NODE_GROUP_TEMPLATE_UPDATE_SCHEMA = copy.copy(NODE_GROUP_TEMPLATE_SCHEMA)
NODE_GROUP_TEMPLATE_UPDATE_SCHEMA["required"] = []
