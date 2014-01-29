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

import savanna.exceptions as ex
from savanna.service.edp import api
import savanna.service.validations.base as main_base
import savanna.service.validations.edp.base as b


MR_EXEC_SCHEMA = {
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
        "cluster_id"
    ]
}


JAVA_EXEC_SCHEMA = {
    "type": "object",
    "properties": {
        "main_class": {
            "type": "string",
        },
        "java_opts": {
            "type": "string",
        },
        "cluster_id": {
            "type": "string",
            "format": "uuid",
        },
        "job_configs": b.job_configs,
    },
    "additionalProperties": False,
    "required": [
        "cluster_id",
        "main_class",
    ]
}


JOB_EXEC_SCHEMA = {
    "oneOf": [MR_EXEC_SCHEMA, JAVA_EXEC_SCHEMA]
}


def _streaming_present(data):
    try:
        streaming = set(('edp.streaming.mapper',
                         'edp.streaming.reducer'))
        configs = set(data['job_configs']['configs'])
        return streaming.intersection(configs) == streaming
    except Exception:
        return False


def check_job_executor(data, job_id):
    job = api.get_job(job_id)

    # Since we allow the creation of MapReduce jobs without libs,
    # ensure here that streaming values are set if the job has
    # no libs
    if job.type == 'MapReduce':
        if not job.libs and not _streaming_present(data):
            raise ex.InvalidDataException("MapReduce job without libs "
                                          "must specify streaming mapper "
                                          "and reducer")

    # Make sure we have the right schema for the job type
    # We can identify the Java action schema by looking for 'main_class'
    if ('main_class' in data) ^ (job.type == 'Java'):
        raise ex.InvalidDataException("Schema is not valid for job type %s"
                                      % job.type)

    if 'input_id' in data:
        b.check_data_source_exists(data['input_id'])
        b.check_data_source_exists(data['output_id'])

    main_base.check_cluster_exists(data['cluster_id'])
