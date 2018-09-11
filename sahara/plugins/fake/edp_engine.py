# Copyright (c) 2014 Mirantis Inc.
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

from sahara.service.edp import base_engine
from sahara.service.validations.edp import job_execution as j
from sahara.utils import edp


class FakeJobEngine(base_engine.JobEngine):
    def cancel_job(self, job_execution):
        pass

    def get_job_status(self, job_execution):
        pass

    def run_job(self, job_execution):
        return 'engine_job_id', edp.JOB_STATUS_SUCCEEDED, None

    def run_scheduled_job(self, job_execution):
        pass

    def validate_job_execution(self, cluster, job, data):
        if job.type == edp.JOB_TYPE_SHELL:
            return
        # All other types except Java require input and output
        # objects and Java require main class
        if job.type in [edp.JOB_TYPE_JAVA, edp.JOB_TYPE_SPARK]:
            j.check_main_class_present(data, job)
        else:
            j.check_data_sources(data, job)

            job_type, subtype = edp.split_job_type(job.type)
            if job_type == edp.JOB_TYPE_MAPREDUCE and (
                    subtype == edp.JOB_SUBTYPE_STREAMING):
                j.check_streaming_present(data, job)

    @staticmethod
    def get_possible_job_config(job_type):
        return None

    @staticmethod
    def get_supported_job_types():
        return edp.JOB_TYPES_ALL
