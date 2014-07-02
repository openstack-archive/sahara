# Copyright (c) 2014 OpenStack Foundation
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


class SparkJobEngine(base_engine.JobEngine):
    def __init__(self, cluster):
        self.cluster = cluster

    def cancel_job(self, job_execution):
        return job_execution

    def get_job_status(self, job_execution):
        return {"status": "FAILED"}

    def run_job(self, job_execution):
        return 0
