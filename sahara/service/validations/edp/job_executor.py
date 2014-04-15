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

import sahara.exceptions as ex
from sahara.service.edp import api
import sahara.service.validations.base as main_base
import sahara.service.validations.edp.base as b
from sahara.utils import edp

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
        "cluster_id"
    ]
}


def _is_main_class_present(data):
    return data and 'edp.java.main_class' in data.get('job_configs',
                                                      {}).get('configs', {})


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
    job_type, subtype = edp.split_job_type(job.type)

    # Check if cluster contains Oozie service to run job
    main_base.check_edp_job_support(data['cluster_id'])

    # All types except Java require input and output objects
    if job_type == 'Java':
        if not _is_main_class_present(data):
            raise ex.InvalidDataException('Java job must '
                                          'specify edp.java.main_class')
    else:
        if not ('input_id' in data and 'output_id' in data):
            raise ex.InvalidDataException("%s job requires 'input_id' "
                                          "and 'output_id'" % job.type)

        b.check_data_source_exists(data['input_id'])
        b.check_data_source_exists(data['output_id'])

        b.check_data_sources_are_different(data['input_id'], data['output_id'])

        if job_type == 'MapReduce' and (
                subtype == 'Streaming' and not _streaming_present(data)):
            raise ex.InvalidDataException("%s job "
                                          "must specify streaming mapper "
                                          "and reducer" % job.type)

    main_base.check_cluster_exists(data['cluster_id'])
