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


from sahara import conductor
from sahara import context
from sahara.i18n import _
from sahara.plugins.ambari import common as p_common
from sahara.plugins.ambari import deploy
from sahara.plugins.ambari import validation
from sahara.plugins import provisioning as p
from sahara.plugins import utils as plugin_utils


conductor = conductor.API


class AmbariPluginProvider(p.ProvisioningPluginBase):

    def get_title(self):
        return "HDP Plugin"

    def get_description(self):
        return _("HDP plugin with Ambari")

    def get_versions(self):
        return ["2.3", "2.2"]

    def get_node_processes(self, hadoop_version):
        return {
            "Ambari": [p_common.AMBARI_SERVER]
        }

    def get_configs(self, hadoop_version):
        return []

    def configure_cluster(self, cluster):
        deploy.setup_ambari(cluster)
        deploy.setup_agents(cluster)
        deploy.wait_ambari_accessible(cluster)
        deploy.update_default_ambari_password(cluster)
        cluster = conductor.cluster_get(context.ctx(), cluster.id)
        deploy.wait_host_registration(cluster)

    def start_cluster(self, cluster):
        self._set_cluster_info(cluster)

    def _set_cluster_info(self, cluster):
        ambari_ip = plugin_utils.get_instance(
            cluster, p_common.AMBARI_SERVER).management_ip
        ambari_port = "8080"
        info = {
            p_common.AMBARI_SERVER: {
                "Web UI": "http://{host}:{port}".format(host=ambari_ip,
                                                        port=ambari_port),
                "Username": "admin",
                "Password": cluster.extra["ambari_password"]
            }
        }
        info.update(cluster.info.to_dict())
        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {"info": info})
        cluster = conductor.cluster_get(ctx, cluster.id)

    def validate(self, cluster):
        validation.validate_creation(cluster.id)

    def scale_cluster(self, cluster, instances):
        pass

    def decommission_nodes(self, cluster, instances):
        pass

    def validate_scaling(self, cluster, existing, additional):
        pass

    def get_edp_engine(self, cluster, job_type):
        pass

    def get_edp_job_types(self, versions=None):
        pass

    def get_edp_config_hints(self, job_type, version):
        pass

    def get_open_ports(self, node_group):
        ports_map = {
            p_common.AMBARI_SERVER: [8080]
        }
        ports = []
        for service in node_group.node_processes:
            ports.extend(ports_map.get(service, []))
        return ports
