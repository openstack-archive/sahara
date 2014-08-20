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

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp.spark import engine as edp_engine


class EdpEngine(edp_engine.SparkJobEngine):
    def validate_job_execution(self, cluster, job, data):
        if cluster.hadoop_version < "1.0.0":
            raise ex.InvalidDataException(
                _('Spark 1.0.0 or higher required to run spark %s jobs')
                % job.type)

        super(EdpEngine, self).validate_job_execution(cluster, job, data)
