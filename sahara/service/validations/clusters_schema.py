# Copyright (c) 2015 Mirantis Inc.
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
from sahara.service.health import verification_base
import sahara.service.validations.cluster_template_schema as ct_schema
from sahara.service.validations import shares


def _build_node_groups_schema():
    schema = copy.deepcopy(ct_schema.CLUSTER_TEMPLATE_SCHEMA)
    return schema['properties']['node_groups']


def _build_cluster_schema(api_version='v1'):
    if api_version == 'v1':
        cluster_schema = copy.deepcopy(ct_schema.CLUSTER_TEMPLATE_SCHEMA)
    elif api_version == 'v2':
        cluster_schema = copy.deepcopy(ct_schema.CLUSTER_TEMPLATE_SCHEMA_V2)
    else:
        raise ex.InvalidDataException('Invalid API version %s' % api_version)

    cluster_schema['properties'].update({
        "is_transient": {
            "type": "boolean"
        },
        "user_keypair_id": {
            "type": "string",
            "format": "valid_keypair_name",
        },
        "cluster_template_id": {
            "type": "string",
            "format": "uuid",
        }})

    if api_version == 'v2':
        cluster_schema['properties'].update({
            "count": {
                "type": "integer"
            }})
    return cluster_schema


CLUSTER_SCHEMA = _build_cluster_schema()
CLUSTER_SCHEMA_V2 = _build_cluster_schema('v2')

MULTIPLE_CLUSTER_SCHEMA = copy.deepcopy(CLUSTER_SCHEMA)
MULTIPLE_CLUSTER_SCHEMA['properties'].update({
    "count": {
        "type": "integer"
    }})
MULTIPLE_CLUSTER_SCHEMA['required'].append('count')

CLUSTER_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {
            "type": ["string", "null"]
        },
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50,
            "format": "valid_name_hostname",
        },
        "is_public": {
            "type": ["boolean", "null"],
        },
        "is_protected": {
            "type": ["boolean", "null"],
        },
        "verification": {
            "type": "object",
            "properties": {
                "status": {
                    "enum": verification_base.get_possible_ops(),
                }
            },
        },
        "shares": copy.deepcopy(shares.SHARE_SCHEMA),
    },
    "additionalProperties": False,
    "required": []
}
CLUSTER_UPDATE_SCHEMA_V2 = copy.deepcopy(CLUSTER_UPDATE_SCHEMA)
CLUSTER_UPDATE_SCHEMA_V2['properties'].update({
    "update_keypair": {
        "type": ["boolean", "null"]
    }})

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

CLUSTER_SCALING_SCHEMA_V2 = copy.deepcopy(CLUSTER_SCALING_SCHEMA)
CLUSTER_SCALING_SCHEMA_V2['properties']['resize_node_groups'][
    'items']['properties'].update(
        {
            "instances": {
                "type": "array",
                "items": {
                    "type": "string",
                },
            }
        })

CLUSTER_DELETE_SCHEMA_V2 = {
    "type": "object",
    "properties": {
        "force": {
            "type": "boolean"
        }
    },
    "additionalProperties": False,
    "required": []
}
