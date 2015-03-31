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

from sahara.plugins.cdh import confighints_helper as ch_helper
from sahara.plugins.cdh.v5 import cloudera_utils as cu
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.service.edp import hdfs_helper
from sahara.service.edp.oozie import engine as edp_engine
from sahara.utils import edp

CU = cu.ClouderaUtilsV5()


class EdpOozieEngine(edp_engine.OozieJobEngine):

    def get_hdfs_user(self):
        return 'hdfs'

    def create_hdfs_dir(self, remote, dir_name):
        hdfs_helper.create_dir_hadoop2(remote, dir_name, self.get_hdfs_user())

    def get_oozie_server_uri(self, cluster):
        oozie_ip = CU.pu.get_oozie(cluster).management_ip
        return 'http://%s:11000/oozie' % oozie_ip

    def get_name_node_uri(self, cluster):
        namenode_ip = CU.pu.get_namenode(cluster).fqdn()
        return 'hdfs://%s:8020' % namenode_ip

    def get_resource_manager_uri(self, cluster):
        resourcemanager_ip = CU.pu.get_resourcemanager(cluster).fqdn()
        return '%s:8032' % resourcemanager_ip

    def get_oozie_server(self, cluster):
        return CU.pu.get_oozie(cluster)

    def validate_job_execution(self, cluster, job, data):
        oo_count = u.get_instances_count(cluster, 'OOZIE_SERVER')
        if oo_count != 1:
            raise ex.InvalidComponentCountException(
                'OOZIE_SERVER', '1', oo_count)

        super(EdpOozieEngine, self).validate_job_execution(cluster, job, data)

    @staticmethod
    def get_possible_job_config(job_type):
        if edp.compare_job_type(job_type, edp.JOB_TYPE_HIVE):
            return {'job_config': ch_helper.get_possible_hive_config_from(
                    'plugins/cdh/v5/resources/hive-site.xml')}
        if edp.compare_job_type(job_type,
                                edp.JOB_TYPE_MAPREDUCE,
                                edp.JOB_TYPE_MAPREDUCE_STREAMING):
            return {'job_config': ch_helper.get_possible_mapreduce_config_from(
                    'plugins/cdh/v5/resources/mapred-site.xml')}
        if edp.compare_job_type(job_type, edp.JOB_TYPE_PIG):
            return {'job_config': ch_helper.get_possible_pig_config_from(
                    'plugins/cdh/v5/resources/mapred-site.xml')}
        return edp_engine.OozieJobEngine.get_possible_job_config(job_type)
