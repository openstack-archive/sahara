# Copyright (c) 2015 Red Hat, Inc.
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

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import utils as plugin_utils
from sahara.plugins.vanilla import confighints_helper as ch_helper
from sahara.plugins.vanilla.hadoop2 import edp_engine
from sahara.plugins.vanilla import utils as v_utils
from sahara.service.edp.spark import engine as edp_spark_engine
from sahara.utils import edp


class EdpOozieEngine(edp_engine.EdpOozieEngine):
    @staticmethod
    def get_possible_job_config(job_type):
        if edp.compare_job_type(job_type, edp.JOB_TYPE_HIVE):
            return {'job_config': ch_helper.get_possible_hive_config_from(
                    'plugins/vanilla/v2_7_1/resources/hive-default.xml')}
        if edp.compare_job_type(job_type,
                                edp.JOB_TYPE_MAPREDUCE,
                                edp.JOB_TYPE_MAPREDUCE_STREAMING):
            return {'job_config': ch_helper.get_possible_mapreduce_config_from(
                    'plugins/vanilla/v2_7_1/resources/mapred-default.xml')}
        if edp.compare_job_type(job_type, edp.JOB_TYPE_PIG):
            return {'job_config': ch_helper.get_possible_pig_config_from(
                    'plugins/vanilla/v2_7_1/resources/mapred-default.xml')}
        return edp_engine.EdpOozieEngine.get_possible_job_config(job_type)


class EdpSparkEngine(edp_spark_engine.SparkJobEngine):

    edp_base_version = "2.7.1"

    def __init__(self, cluster):
        super(EdpSparkEngine, self).__init__(cluster)
        self.master = plugin_utils.get_instance(cluster,
                                                "spark history server")
        self.plugin_params["spark-user"] = "sudo -u hadoop "
        self.plugin_params["spark-submit"] = os.path.join(
            plugin_utils.get_config_value_or_default(
                "Spark", "Spark home", self.cluster),
            "bin/spark-submit")
        self.plugin_params["deploy-mode"] = "cluster"
        self.plugin_params["master"] = "yarn"

        driver_cp = plugin_utils.get_config_value_or_default(
            "Spark", "Executor extra classpath", self.cluster)
        self.plugin_params["driver-class-path"] = driver_cp

    @staticmethod
    def edp_supported(version):
        return version >= EdpSparkEngine.edp_base_version

    @staticmethod
    def job_type_supported(job_type):
        return (job_type in
                edp_spark_engine.SparkJobEngine.get_supported_job_types())

    def validate_job_execution(self, cluster, job, data):
        if (not self.edp_supported(cluster.hadoop_version) or
                not v_utils.get_spark_history_server(cluster)):

            raise ex.InvalidDataException(
                _('Spark {base} or higher required to run {type} jobs').format(
                    base=EdpSparkEngine.edp_base_version, type=job.type))

        super(EdpSparkEngine, self).validate_job_execution(cluster, job, data)
