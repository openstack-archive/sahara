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

JOB_BINARY_SCHEMA = {
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
        "url": {
            "type": "string",
            "format": "valid_job_location"
        },
        "is_public": {
            "type": ["boolean", "null"],
        },
        "is_protected": {
            "type": ["boolean", "null"],
        },
        # extra is simple_config for now because we may need not only
        # user-password it the case of external storage
        "extra": {
            "type": "simple_config",
        }
    },
    "additionalProperties": False,
    "required": [
        "name",
        "url"
    ]
}

JOB_BINARY_UPDATE_SCHEMA = copy.copy(JOB_BINARY_SCHEMA)
JOB_BINARY_UPDATE_SCHEMA["required"] = []
