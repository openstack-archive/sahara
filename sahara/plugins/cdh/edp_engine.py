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

from sahara.plugins.cdh import utils as cu
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.service.edp import hdfs_helper
from sahara.service.edp.oozie import engine as edp_engine


class EdpOozieEngine(edp_engine.OozieJobEngine):

    def get_hdfs_user(self):
        return 'hdfs'

    def create_hdfs_dir(self, remote, dir_name):
        hdfs_helper.create_dir_hadoop2(remote, dir_name, self.get_hdfs_user())

    def get_oozie_server_uri(self, cluster):
        oozie_ip = cu.get_oozie(cluster).management_ip
        return 'http://%s:11000/oozie' % oozie_ip

    def get_name_node_uri(self, cluster):
        namenode_ip = cu.get_namenode(cluster).fqdn()
        return 'hdfs://%s:8020' % namenode_ip

    def get_resource_manager_uri(self, cluster):
        resourcemanager_ip = cu.get_resourcemanager(cluster).fqdn()
        return '%s:8032' % resourcemanager_ip

    def get_oozie_server(self, cluster):
        return cu.get_oozie(cluster)

    def validate_job_execution(self, cluster, job, data):
        oo_count = u.get_instances_count(cluster, 'OOZIE_SERVER')
        if oo_count != 1:
            raise ex.InvalidComponentCountException(
                'OOZIE_SERVER', '1', oo_count)

        super(EdpOozieEngine, self).validate_job_execution(cluster, job, data)
