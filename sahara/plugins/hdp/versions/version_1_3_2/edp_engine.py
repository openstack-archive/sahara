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

from sahara.plugins.hdp import confighints_helper as ch_helper
from sahara.plugins.hdp import edp_engine
from sahara.service.edp import hdfs_helper
from sahara.utils import edp


class EdpOozieEngine(edp_engine.EdpOozieEngine):

    def create_hdfs_dir(self, remote, dir_name):
        hdfs_helper.create_dir_hadoop1(remote, dir_name, self.get_hdfs_user())

    @staticmethod
    def get_possible_job_config(job_type):
        if edp.compare_job_type(job_type, edp.JOB_TYPE_HIVE):
            return {'job_config': ch_helper.get_possible_hive_config_from(
                    'plugins/hdp/versions/version_1_3_2/resources/'
                    'ambari-config-resource.json')}
        if edp.compare_job_type(job_type,
                                edp.JOB_TYPE_MAPREDUCE,
                                edp.JOB_TYPE_MAPREDUCE_STREAMING):
            return {'job_config': ch_helper.get_possible_mapreduce_config_from(
                    'plugins/hdp/versions/version_1_3_2/resources/'
                    'ambari-config-resource.json')}
        if edp.compare_job_type(job_type, edp.JOB_TYPE_PIG):
            return {'job_config': ch_helper.get_possible_pig_config_from(
                    'plugins/hdp/versions/version_1_3_2/resources/'
                    'ambari-config-resource.json')}
        return edp_engine.EdpOozieEngine.get_possible_job_config(job_type)

    def get_resource_manager_uri(self, cluster):
        return cluster['info']['MapReduce']['JobTracker']
