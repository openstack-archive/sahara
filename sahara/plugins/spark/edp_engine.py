# Copyright (c) 2014 Mirantis Inc.
# Copyright (c) 2015 ISPRAS
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

import os

import six

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import utils as plugin_utils
from sahara.service.edp.spark import engine as edp_engine


class EdpEngine(edp_engine.SparkJobEngine):

    edp_base_version = "1.3.1"

    def __init__(self, cluster):
        super(EdpEngine, self).__init__(cluster)
        self.master = plugin_utils.get_instance(cluster, "master")
        self.plugin_params["spark-user"] = ""
        self.plugin_params["spark-submit"] = os.path.join(
            plugin_utils.
            get_config_value_or_default("Spark", "Spark home", self.cluster),
            "bin/spark-submit")
        self.plugin_params["deploy-mode"] = "client"
        port_str = six.text_type(
            plugin_utils.get_config_value_or_default(
                "Spark", "Master port", self.cluster))
        self.plugin_params["master"] = ('spark://%(host)s:' + port_str)
        driver_cp = plugin_utils.get_config_value_or_default(
            "Spark", "Executor extra classpath", self.cluster)
        self.plugin_params["driver-class-path"] = driver_cp

    @staticmethod
    def edp_supported(version):
        return version >= EdpEngine.edp_base_version

    @staticmethod
    def job_type_supported(job_type):
        return job_type in edp_engine.SparkJobEngine.get_supported_job_types()

    def validate_job_execution(self, cluster, job, data):
        if not self.edp_supported(cluster.hadoop_version):
            raise ex.InvalidDataException(
                _('Spark {base} or higher required to run {type} jobs').format(
                    base=EdpEngine.edp_base_version, type=job.type))

        super(EdpEngine, self).validate_job_execution(cluster, job, data)
