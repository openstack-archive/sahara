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

import savanna.service.validations.base as main_base
import savanna.service.validations.edp.base as b


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
        "job_configs": b.job_configs,
    },
    "additionalProperties": False,
    "required": [
        "input_id",
        "output_id",
        "cluster_id",
    ]
}


def check_job_executor(data, **kwargs):
    b.check_data_source_exists(data['input_id'])
    b.check_data_source_exists(data['output_id'])
    main_base.check_cluster_exists(data['cluster_id'])
