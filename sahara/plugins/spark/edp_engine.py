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

    edp_base_version = "1.0.0"

    @staticmethod
    def edp_supported(version):
        return version >= EdpEngine.edp_base_version

    def validate_job_execution(self, cluster, job, data):
        if not self.edp_supported(cluster.hadoop_version):
            raise ex.InvalidDataException(
                _('Spark {base} or higher required to run {type} jobs').format(
                    base=EdpEngine.edp_base_version, type=job.type))

        super(EdpEngine, self).validate_job_execution(cluster, job, data)
