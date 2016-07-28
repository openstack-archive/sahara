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

import copy

from sahara.i18n import _
from sahara.plugins.cdh import versionfactory as vhf
from sahara.plugins import provisioning as p


class CDHPluginProvider(p.ProvisioningPluginBase):
    def __init__(self):
        self.version_factory = vhf.VersionFactory.get_instance()

    def get_title(self):
        return "Cloudera Plugin"

    def get_description(self):
        return _('The Cloudera Sahara plugin provides the ability to '
                 'launch the Cloudera distribution of Apache Hadoop '
                 '(CDH) with Cloudera Manager management console.')

    def get_labels(self):
        default = {'enabled': {'status': True}, 'stable': {'status': True}}
        result = {'plugin_labels': copy.deepcopy(default)}
        deprecated = {'enabled': {'status': True},
                      'deprecated': {'status': True}}
        result['version_labels'] = {
            '5.7.0': copy.deepcopy(default),
            '5.5.0': copy.deepcopy(default),
            '5.4.0': copy.deepcopy(deprecated),
            '5.3.0': copy.deepcopy(deprecated),
            '5': copy.deepcopy(deprecated),
        }
        return result

    def _get_version_handler(self, hadoop_version):
        return self.version_factory.get_version_handler(hadoop_version)

    def get_versions(self):
        return self.version_factory.get_versions()

    def get_node_processes(self, hadoop_version):
        return self._get_version_handler(hadoop_version).get_node_processes()

    def get_configs(self, hadoop_version):
        return self._get_version_handler(hadoop_version).get_plugin_configs()

    def configure_cluster(self, cluster):
        return self._get_version_handler(
            cluster.hadoop_version).configure_cluster(cluster)

    def start_cluster(self, cluster):
        return self._get_version_handler(
            cluster.hadoop_version).start_cluster(cluster)

    def validate(self, cluster):
        return self._get_version_handler(
            cluster.hadoop_version).validate(cluster)

    def scale_cluster(self, cluster, instances):
        return self._get_version_handler(
            cluster.hadoop_version).scale_cluster(cluster, instances)

    def decommission_nodes(self, cluster, instances):
        return self._get_version_handler(
            cluster.hadoop_version).decommission_nodes(cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        return self._get_version_handler(
            cluster.hadoop_version).validate_scaling(cluster, existing,
                                                     additional)

    def get_edp_engine(self, cluster, job_type):
        return self._get_version_handler(
            cluster.hadoop_version).get_edp_engine(cluster, job_type)

    def get_edp_job_types(self, versions=None):
        res = {}
        for vers in self.version_factory.get_versions():
            if not versions or vers in versions:
                vh = self.version_factory.get_version_handler(vers)
                res[vers] = vh.get_edp_job_types()
        return res

    def get_edp_config_hints(self, job_type, version):
        version_handler = (
            self.version_factory.get_version_handler(version))
        return version_handler.get_edp_config_hints(job_type)

    def get_open_ports(self, node_group):
        return self._get_version_handler(
            node_group.cluster.hadoop_version).get_open_ports(node_group)

    def recommend_configs(self, cluster, scaling=False):
        return self._get_version_handler(
            cluster.hadoop_version).recommend_configs(cluster, scaling)

    def get_health_checks(self, cluster):
        return self._get_version_handler(
            cluster.hadoop_version).get_health_checks(cluster)
