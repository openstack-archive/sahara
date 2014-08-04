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

from sahara import conductor
from sahara import context
from sahara.plugins.cdh import config_helper as c_helper
from sahara.plugins.cdh import deploy as dp
from sahara.plugins.cdh import utils as cu
from sahara.plugins.cdh import validation as vl
from sahara.plugins import provisioning as p

conductor = conductor.API


class CDHPluginProvider(p.ProvisioningPluginBase):

    def get_title(self):
        return "Cloudera Plugin"

    def get_description(self):
        return ("This plugin provides an ability to launch CDH clusters with"
                "Cloudera Manager management console.")

    def get_versions(self):
        return ['5']

    def get_node_processes(self, hadoop_version):
        return {
            "CLOUDERA": ['MANAGER'],
            "HDFS": [],
            "NAMENODE": ['NAMENODE'],
            "DATANODE": ['DATANODE'],
            "SECONDARYNAMENODE": ['SECONDARYNAMENODE'],
            "YARN": [],
            "RESOURCEMANAGER": ['RESOURCEMANAGER'],
            "NODEMANAGER": ['NODEMANAGER'],
            "JOBHISTORY": ['JOBHISTORY'],
            "OOZIE": ['OOZIE_SERVER']
        }

    def get_configs(self, hadoop_version):
        return c_helper.get_plugin_configs()

    def configure_cluster(self, cluster):
        dp.configure_cluster(cluster)

    def start_cluster(self, cluster):
        dp.start_cluster(cluster)

        self._set_cluster_info(cluster)

    def validate(self, cluster):
        vl.validate_cluster_creating(cluster)

    def scale_cluster(self, cluster, instances):
        dp.scale_cluster(cluster, instances)

    def decommission_nodes(self, cluster, instances):
        dp.decomission_cluster(cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        vl.validate_existing_ng_scaling(cluster, existing)
        vl.validate_additional_ng_scaling(cluster, additional)

    def get_hdfs_user(self):
        return 'hdfs'

    def get_oozie_server(self, cluster):
        return cu.get_oozie(cluster)

    def get_oozie_server_uri(self, cluster):
        oozie_ip = cu.get_oozie(cluster).management_ip
        return 'http://%s:11000/oozie' % oozie_ip

    def get_name_node_uri(self, cluster):
        namenode_ip = cu.get_namenode(cluster).fqdn()
        return 'hdfs://%s:8020' % namenode_ip

    def get_resource_manager_uri(self, cluster):
        resourcemanager_ip = cu.get_resourcemanager(cluster).fqdn()
        return '%s:8032' % resourcemanager_ip

    def _set_cluster_info(self, cluster):
        mng = cu.get_manager(cluster)
        info = {
            'Cloudera Manager': {
                'Web UI': 'http://%s:7180' % mng.management_ip,
                'Username': 'admin',
                'Password': 'admin'
            }
        }

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})
