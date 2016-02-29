# Copyright (c) 2015 Intel Corporation
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

from sahara.plugins.cdh import confighints_helper as ch_helper
from sahara.plugins.cdh import edp_engine
from sahara.plugins.cdh.v5_5_0 import cloudera_utils as cu
from sahara.service.edp.oozie import engine as oozie_engine
from sahara.utils import edp


class EdpOozieEngine(edp_engine.EdpOozieEngine):

    def __init__(self, cluster):
        super(EdpOozieEngine, self).__init__(cluster)
        self.cloudera_utils = cu.ClouderaUtilsV550()

    def get_name_node_uri(self, cluster):
        if len(self.cloudera_utils.pu.get_jns(cluster)) > 0:
            return 'hdfs://%s' % self.cloudera_utils.NAME_SERVICE
        else:
            namenode_ip = self.cloudera_utils.pu.get_namenode(cluster).fqdn()
            return 'hdfs://%s:8020' % namenode_ip

    @staticmethod
    def get_possible_job_config(job_type):
        if edp.compare_job_type(job_type, edp.JOB_TYPE_HIVE):
            return {'job_config': ch_helper.get_possible_hive_config_from(
                    'plugins/cdh/v5_5_0/resources/hive-site.xml')}
        if edp.compare_job_type(job_type,
                                edp.JOB_TYPE_MAPREDUCE,
                                edp.JOB_TYPE_MAPREDUCE_STREAMING):
            return {'job_config': ch_helper.get_possible_mapreduce_config_from(
                    'plugins/cdh/v5_5_0/resources/mapred-site.xml')}
        if edp.compare_job_type(job_type, edp.JOB_TYPE_PIG):
            return {'job_config': ch_helper.get_possible_pig_config_from(
                    'plugins/cdh/v5_5_0/resources/mapred-site.xml')}
        return oozie_engine.OozieJobEngine.get_possible_job_config(job_type)


class EdpSparkEngine(edp_engine.EdpSparkEngine):

    edp_base_version = "5.5.0"
