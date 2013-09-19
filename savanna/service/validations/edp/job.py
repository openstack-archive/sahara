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

import savanna.service.validations.edp.base as b

JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50
        },
        "description": {
            "type": "string"
        },
        "type": {
            "type": "string",
            "enum": [
                "Pig",
                "Hive",
                "Oozie",
                "Jar",
                "StreamingAPI"
            ],
        },
        "job_origin_id": {
            "type": "string",
            "format": "uuid",
        },
        "input_type": b.data_source_type,
        "output_type": b.data_source_type,
        "job_configs": b.job_configs,
    },
    "additionalProperties": False,
    "required": [
        "name",
        "type",
        "job_origin_id"
    ]
}


def check_job_create(data, **kwargs):
    b.check_job_unique_name(data['name'])
