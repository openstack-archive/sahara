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

from sahara.service.validations import shares

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
            "type": "flavor",
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
            "type": ["string", "null"],
            "format": "uuid",
        },
        "node_configs": {
            "type": ["configs", "null"],
        },
        "volumes_per_node": {
            "type": "integer",
            "minimum": 0,
        },
        "volumes_size": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "volume_type": {
            "type": ["string", "null"],
        },
        "volumes_availability_zone": {
            "type": ["string", "null"],
        },
        "volume_mount_prefix": {
            "type": ["string", "null"],
            "format": "posix_path",
        },
        "description": {
            "type": ["string", "null"],
        },
        "floating_ip_pool": {
            "type": ["string", "null"],
        },
        "security_groups": {
            "type": ["array", "null"],
            "items": {"type": "string"}
        },
        "auto_security_group": {
            "type": ["boolean", "null"],
        },
        "availability_zone": {
            "type": ["string", "null"],
        },
        "is_proxy_gateway": {
            "type": ["boolean", "null"],
        },
        "volume_local_to_instance": {
            "type": ["boolean", "null"]
        },
        "shares": copy.deepcopy(shares.SHARE_SCHEMA),
        "use_autoconfig": {
            "type": ["boolean", "null"]
        },
        "is_public": {
            "type": ["boolean", "null"],
        },
        "is_protected": {
            "type": ["boolean", "null"],
        }
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

# APIv2: renaming hadoop_version -> plugin_version
NODE_GROUP_TEMPLATE_SCHEMA_V2 = copy.deepcopy(NODE_GROUP_TEMPLATE_SCHEMA)
del NODE_GROUP_TEMPLATE_SCHEMA_V2["properties"]["hadoop_version"]
NODE_GROUP_TEMPLATE_SCHEMA_V2["required"].remove("hadoop_version")
NODE_GROUP_TEMPLATE_SCHEMA_V2["properties"].update({
    "plugin_version": {
        "type": "string",
    }})
NODE_GROUP_TEMPLATE_SCHEMA_V2["required"].append("plugin_version")
NODE_GROUP_TEMPLATE_SCHEMA_V2["properties"].update({
    "boot_from_volume": {
        "type": "boolean",
    },
    "boot_volume_type": {
        "type": "string",
    },
    "boot_volume_availability_zone": {
        "type": "string",
    },
    "boot_volume_local_to_instance": {
        "type": "boolean",
    }})


# For an update we do not require any fields but we want the given
# fields to be validated
NODE_GROUP_TEMPLATE_UPDATE_SCHEMA = copy.copy(NODE_GROUP_TEMPLATE_SCHEMA)
NODE_GROUP_TEMPLATE_UPDATE_SCHEMA["required"] = []

NODE_GROUP_TEMPLATE_UPDATE_SCHEMA_V2 = copy.copy(NODE_GROUP_TEMPLATE_SCHEMA_V2)
NODE_GROUP_TEMPLATE_UPDATE_SCHEMA_V2["required"] = []
