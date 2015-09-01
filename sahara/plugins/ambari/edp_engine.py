# Copyright (c) 2015 Mirantis Inc.
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

from sahara.plugins.ambari import common as p_common
from sahara.plugins import exceptions as pex
from sahara.plugins import utils as plugin_utils
from sahara.service.edp import hdfs_helper
from sahara.service.edp.oozie import engine as oozie_engine


class EDPOozieEngine(oozie_engine.OozieJobEngine):
    def get_hdfs_user(self):
        return "oozie"

    def create_hdfs_dir(self, remote, dir_name):
        hdfs_helper.create_dir_hadoop2(remote, dir_name, self.get_hdfs_user())

    def get_oozie_server_uri(self, cluster):
        oozie = plugin_utils.get_instance(cluster, p_common.OOZIE_SERVER)
        return "http://%s:11000/oozie" % oozie.management_ip

    def get_name_node_uri(self, cluster):
        namenode = plugin_utils.get_instance(cluster, p_common.NAMENODE)
        return "hdfs://%s:8020" % namenode.fqdn()

    def get_resource_manager_uri(self, cluster):
        resourcemanager = plugin_utils.get_instance(cluster,
                                                    p_common.RESOURCEMANAGER)
        return "%s:8050" % resourcemanager.fqdn()

    def get_oozie_server(self, cluster):
        return plugin_utils.get_instance(cluster, p_common.OOZIE_SERVER)

    def validate_job_execution(self, cluster, job, data):
        oozie_count = plugin_utils.get_instances_count(cluster,
                                                       p_common.OOZIE_SERVER)
        if oozie_count != 1:
            raise pex.InvalidComponentCountException(
                p_common.OOZIE_SERVER, "1", oozie_count)
        super(EDPOozieEngine, self).validate_job_execution(cluster, job, data)

    @staticmethod
    def get_possible_job_config(job_type):
        return {"job_config": []}
