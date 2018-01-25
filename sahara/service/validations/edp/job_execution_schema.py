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

import sahara.service.validations.edp.base as b


JOB_EXEC_SCHEMA = {
    "type": "object",
    "properties": {
        "input_id": {
            "type": "string",
            "format": "uuid",
        },
        "output_id": {
            "type": "string",
            "format": "uuid",
        },
        "cluster_id": {
            "type": "string",
            "format": "uuid",
        },
        "interface": {
            "type": "simple_config",
        },
        "job_configs": b.job_configs,
        "is_public": {
            "type": ["boolean", "null"],
        },
        "is_protected": {
            "type": ["boolean", "null"],
        }
    },
    "additionalProperties": False,
    "required": [
        "cluster_id"
    ]
}


JOB_EXEC_SCHEMA_V2 = copy.deepcopy(JOB_EXEC_SCHEMA)
JOB_EXEC_SCHEMA_V2['properties'].update({
    "job_template_id": {
        "type": "string",
        "format": "uuid",
    }})
JOB_EXEC_SCHEMA_V2['required'].append('job_template_id')


JOB_EXEC_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_public": {
            "type": ["boolean", "null"],
        },
        "is_protected": {
            "type": ["boolean", "null"],
        },
        "info": {
            "type": "simple_config",
            "properties": {
                    "status": {
                        "enum": ["suspend", "cancel"]
                    }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False,
    "required": []
}
