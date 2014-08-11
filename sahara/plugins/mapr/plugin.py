# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.


import sahara.plugins.mapr.versions.version_handler_factory as vhf
import sahara.plugins.provisioning as p


class MapRPlugin(p.ProvisioningPluginBase):
    title = 'MapR Hadoop Distribution'
    description = ('The MapR Distribution provides a full Hadoop stack that'
                   ' includes the MapR File System (MapR-FS), MapReduce,'
                   ' a complete Hadoop ecosystem, and the MapR Control System'
                   ' user interface')
    hdfs_user = 'mapr'

    def _get_handler(self, hadoop_version):
        return vhf.VersionHandlerFactory.get().get_handler(hadoop_version)

    def get_title(self):
        return MapRPlugin.title

    def get_description(self):
        return MapRPlugin.description

    def get_hdfs_user(self):
        return MapRPlugin.hdfs_user

    def get_versions(self):
        return vhf.VersionHandlerFactory.get().get_versions()

    def get_node_processes(self, hadoop_version):
        return self._get_handler(hadoop_version).get_node_processes()

    def get_configs(self, hadoop_version):
        return self._get_handler(hadoop_version).get_configs()

    def configure_cluster(self, cluster):
        self._get_handler(cluster.hadoop_version).configure_cluster(cluster)

    def start_cluster(self, cluster):
        self._get_handler(cluster.hadoop_version).start_cluster(cluster)

    def validate(self, cluster):
        self._get_handler(cluster.hadoop_version).validate(cluster)

    def validate_scaling(self, cluster, existing, additional):
        v_handler = self._get_handler(cluster.hadoop_version)
        v_handler.validate_scaling(cluster, existing, additional)

    def scale_cluster(self, cluster, instances):
        v_handler = self._get_handler(cluster.hadoop_version)
        v_handler.scale_cluster(cluster, instances)

    def decommission_nodes(self, cluster, instances):
        v_handler = self._get_handler(cluster.hadoop_version)
        v_handler.decommission_nodes(cluster, instances)

    def get_oozie_server(self, cluster):
        v_handler = self._get_handler(cluster.hadoop_version)
        return v_handler.get_oozie_server(cluster)

    def get_name_node_uri(self, cluster):
        v_handler = self._get_handler(cluster.hadoop_version)
        return v_handler.get_name_node_uri(cluster)

    def get_oozie_server_uri(self, cluster):
        v_handler = self._get_handler(cluster.hadoop_version)
        return v_handler.get_oozie_server_uri(cluster)

    def get_resource_manager_uri(self, cluster):
        v_handler = self._get_handler(cluster.hadoop_version)
        return v_handler.get_resource_manager_uri(cluster)

    def get_edp_engine(self, cluster, job_type):
        v_handler = self._get_handler(cluster.hadoop_version)
        return v_handler.get_edp_engine(cluster, job_type)
