# Copyright (c) 2015 OpenStack Foundation
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

from sahara.plugins import utils as plugin_utils
from sahara.service.edp.spark import engine as shell_engine


class ShellEngine(shell_engine.SparkShellJobEngine):
    def __init__(self, cluster):
        super(ShellEngine, self).__init__(cluster)
        self.master = plugin_utils.get_instance(cluster, "master")

    @staticmethod
    def job_type_supported(job_type):
        return (job_type in shell_engine.SparkShellJobEngine.
                get_supported_job_types())
