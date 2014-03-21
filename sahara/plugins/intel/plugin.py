# Copyright (c) 2013 Intel Corporation
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

from sahara.plugins.general import utils as u
from sahara.plugins.intel import versionfactory as vhf
from sahara.plugins import provisioning as p


class IDHProvider(p.ProvisioningPluginBase):
    def __init__(self):
        self.version_factory = vhf.VersionFactory.get_instance()

    def get_description(self):
        return \
            'The IDH OpenStack plugin works with project ' \
            'Sahara to automate the deployment of the Intel Distribution ' \
            'of Apache Hadoop on OpenStack based ' \
            'public & private clouds'

    def _get_version_handler(self, hadoop_version):
        return self.version_factory.get_version_handler(hadoop_version)

    def get_hdfs_user(self):
        return 'hadoop'

    def get_node_processes(self, hadoop_version):
        return self._get_version_handler(hadoop_version).get_node_processes()

    def get_versions(self):
        return self.version_factory.get_versions()

    def get_title(self):
        return "Intel(R) Distribution for Apache Hadoop* Software"

    def get_configs(self, hadoop_version):
        return self._get_version_handler(hadoop_version).get_plugin_configs()

    def configure_cluster(self, cluster):
        self._get_version_handler(
            cluster.hadoop_version).configure_cluster(cluster)

    def start_cluster(self, cluster):
        self._get_version_handler(
            cluster.hadoop_version).start_cluster(cluster)

    def validate(self, cluster):
        self._get_version_handler(
            cluster.hadoop_version).validate(cluster)

    def scale_cluster(self, cluster, instances):
        self._get_version_handler(
            cluster.hadoop_version).scale_cluster(cluster, instances)

    def decommission_nodes(self, cluster, instances):
        self._get_version_handler(
            cluster.hadoop_version).decommission_nodes(cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        self._get_version_handler(cluster.hadoop_version).validate_scaling(
            cluster, existing, additional)

    def get_oozie_server(self, cluster):
        return u.get_instance(cluster, "oozie")

    def get_resource_manager_uri(self, cluster):
        return self._get_version_handler(
            cluster.hadoop_version).get_resource_manager_uri(cluster)
