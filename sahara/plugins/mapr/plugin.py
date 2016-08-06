# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from sahara.i18n import _
import sahara.plugins.mapr.versions.version_handler_factory as vhf
import sahara.plugins.provisioning as p


class MapRPlugin(p.ProvisioningPluginBase):
    title = 'MapR Hadoop Distribution'
    description = _('The MapR Distribution provides a full Hadoop stack that'
                    ' includes the MapR File System (MapR-FS), MapReduce,'
                    ' a complete Hadoop ecosystem, and the MapR Control System'
                    ' user interface')

    def _get_handler(self, hadoop_version):
        return vhf.VersionHandlerFactory.get().get_handler(hadoop_version)

    def get_title(self):
        return MapRPlugin.title

    def get_description(self):
        return MapRPlugin.description

    def get_labels(self):
        return {
            'plugin_labels': {'enabled': {'status': True}},
            'version_labels': {
                '5.1.0.mrv2': {'enabled': {'status': True}},
                '5.0.0.mrv2': {'enabled': {'status': False},
                               'deprecated': {'status': True}}
            }
        }

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

    def get_edp_engine(self, cluster, job_type):
        v_handler = self._get_handler(cluster.hadoop_version)
        return v_handler.get_edp_engine(cluster, job_type)

    def get_edp_job_types(self, versions=None):
        res = {}
        for vers in self.get_versions():
            if not versions or vers in versions:
                vh = self._get_handler(vers)
                res[vers] = vh.get_edp_job_types()
        return res

    def get_edp_config_hints(self, job_type, version):
        v_handler = self._get_handler(version)
        return v_handler.get_edp_config_hints(job_type)

    def get_open_ports(self, node_group):
        v_handler = self._get_handler(node_group.cluster.hadoop_version)
        return v_handler.get_open_ports(node_group)
