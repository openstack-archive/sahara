# Copyright (c) 2015 Red Hat Inc.
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

import sahara.service.validations.edp.base as b

DATA_SOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50,
            "format": "valid_name"
        },
        "description": {
            "type": "string"
        },
        "type": b.data_source_type,
        "url": {
            "type": "string",
        },
        "credentials": {
            "type": "object"
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
        "type",
        "url"
    ]
}

# For an update we do not require any fields but we want the given
# fields to be validated
DATA_SOURCE_UPDATE_SCHEMA = copy.copy(DATA_SOURCE_SCHEMA)
DATA_SOURCE_UPDATE_SCHEMA["required"] = []
