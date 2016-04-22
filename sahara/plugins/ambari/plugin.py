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
from sahara.plugins.ambari import configs
from sahara.plugins.ambari import deploy
from sahara.plugins.ambari import edp_engine
from sahara.plugins.ambari import health
from sahara.plugins.ambari import validation
from sahara.plugins import provisioning as p
from sahara.plugins import utils as plugin_utils
from sahara.swift import swift_helper


conductor = conductor.API


class AmbariPluginProvider(p.ProvisioningPluginBase):

    def get_title(self):
        return "HDP Plugin"

    def get_description(self):
        return _("HDP plugin with Ambari")

    def get_versions(self):
        return ["2.3"]

    def get_node_processes(self, hadoop_version):
        return {
            p_common.AMBARI_SERVICE: [p_common.AMBARI_SERVER],
            p_common.FALCON_SERVICE: [p_common.FALCON_SERVER],
            p_common.FLUME_SERVICE: [p_common.FLUME_HANDLER],
            p_common.HBASE_SERVICE: [p_common.HBASE_MASTER,
                                     p_common.HBASE_REGIONSERVER],
            p_common.HDFS_SERVICE: [p_common.DATANODE, p_common.NAMENODE,
                                    p_common.SECONDARY_NAMENODE,
                                    p_common.JOURNAL_NODE],
            p_common.HIVE_SERVICE: [p_common.HIVE_METASTORE,
                                    p_common.HIVE_SERVER],
            p_common.KAFKA_SERVICE: [p_common.KAFKA_BROKER],
            p_common.KNOX_SERVICE: [p_common.KNOX_GATEWAY],
            p_common.OOZIE_SERVICE: [p_common.OOZIE_SERVER],
            p_common.RANGER_SERVICE: [p_common.RANGER_ADMIN,
                                      p_common.RANGER_USERSYNC],
            p_common.SLIDER_SERVICE: [p_common.SLIDER],
            p_common.SPARK_SERVICE: [p_common.SPARK_JOBHISTORYSERVER],
            p_common.SQOOP_SERVICE: [p_common.SQOOP],
            p_common.STORM_SERVICE: [
                p_common.DRPC_SERVER, p_common.NIMBUS,
                p_common.STORM_UI_SERVER, p_common.SUPERVISOR],
            p_common.YARN_SERVICE: [
                p_common.APP_TIMELINE_SERVER, p_common.HISTORYSERVER,
                p_common.NODEMANAGER, p_common.RESOURCEMANAGER],
            p_common.ZOOKEEPER_SERVICE: [p_common.ZOOKEEPER_SERVER],
        }

    def get_configs(self, hadoop_version):
        return configs.load_configs(hadoop_version)

    def configure_cluster(self, cluster):
        deploy.disable_repos(cluster)
        deploy.setup_ambari(cluster)
        deploy.setup_agents(cluster)
        deploy.wait_ambari_accessible(cluster)
        deploy.update_default_ambari_password(cluster)
        cluster = conductor.cluster_get(context.ctx(), cluster.id)
        deploy.wait_host_registration(cluster,
                                      plugin_utils.get_instances(cluster))
        deploy.set_up_hdp_repos(cluster)
        deploy.create_blueprint(cluster)

    def start_cluster(self, cluster):
        self._set_cluster_info(cluster)
        deploy.start_cluster(cluster)
        cluster_instances = plugin_utils.get_instances(cluster)
        swift_helper.install_ssl_certs(cluster_instances)
        deploy.add_hadoop_swift_jar(cluster_instances)

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
        nns = plugin_utils.get_instances(cluster, p_common.NAMENODE)
        info[p_common.NAMENODE] = {}
        for idx, namenode in enumerate(nns):
            info[p_common.NAMENODE][
                "Web UI %s" % (idx + 1)] = (
                "http://%s:50070" % namenode.management_ip)

        rms = plugin_utils.get_instances(cluster, p_common.RESOURCEMANAGER)
        info[p_common.RESOURCEMANAGER] = {}
        for idx, resourcemanager in enumerate(rms):
            info[p_common.RESOURCEMANAGER][
                "Web UI %s" % (idx + 1)] = (
                "http://%s:8088" % resourcemanager.management_ip)

        historyserver = plugin_utils.get_instance(cluster,
                                                  p_common.HISTORYSERVER)
        if historyserver:
            info[p_common.HISTORYSERVER] = {
                "Web UI": "http://%s:19888" % historyserver.management_ip
            }
        atlserver = plugin_utils.get_instance(cluster,
                                              p_common.APP_TIMELINE_SERVER)
        if atlserver:
            info[p_common.APP_TIMELINE_SERVER] = {
                "Web UI": "http://%s:8188" % atlserver.management_ip
            }
        oozie = plugin_utils.get_instance(cluster, p_common.OOZIE_SERVER)
        if oozie:
            info[p_common.OOZIE_SERVER] = {
                "Web UI": "http://%s:11000/oozie" % oozie.management_ip
            }
        hbase_master = plugin_utils.get_instance(cluster,
                                                 p_common.HBASE_MASTER)
        if hbase_master:
            info[p_common.HBASE_MASTER] = {
                "Web UI": "http://%s:60010" % hbase_master.management_ip
            }
        falcon = plugin_utils.get_instance(cluster, p_common.FALCON_SERVER)
        if falcon:
            info[p_common.FALCON_SERVER] = {
                "Web UI": "http://%s:15000" % falcon.management_ip
            }
        storm_ui = plugin_utils.get_instance(cluster, p_common.STORM_UI_SERVER)
        if storm_ui:
            info[p_common.STORM_UI_SERVER] = {
                "Web UI": "http://%s:8744" % storm_ui.management_ip
            }
        ranger_admin = plugin_utils.get_instance(cluster,
                                                 p_common.RANGER_ADMIN)
        if ranger_admin:
            info[p_common.RANGER_ADMIN] = {
                "Web UI": "http://%s:6080" % ranger_admin.management_ip,
                "Username": "admin",
                "Password": "admin"
            }
        spark_hs = plugin_utils.get_instance(cluster,
                                             p_common.SPARK_JOBHISTORYSERVER)
        if spark_hs:
            info[p_common.SPARK_JOBHISTORYSERVER] = {
                "Web UI": "http://%s:18080" % spark_hs.management_ip
            }
        info.update(cluster.info.to_dict())
        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {"info": info})
        cluster = conductor.cluster_get(ctx, cluster.id)

    def validate(self, cluster):
        validation.validate(cluster.id)

    def scale_cluster(self, cluster, instances):
        deploy.setup_agents(cluster, instances)
        cluster = conductor.cluster_get(context.ctx(), cluster.id)
        deploy.wait_host_registration(cluster, instances)
        deploy.add_new_hosts(cluster, instances)
        deploy.manage_config_groups(cluster, instances)
        deploy.manage_host_components(cluster, instances)
        swift_helper.install_ssl_certs(instances)
        deploy.add_hadoop_swift_jar(instances)

    def decommission_nodes(self, cluster, instances):
        deploy.decommission_hosts(cluster, instances)
        deploy.remove_services_from_hosts(cluster, instances)
        deploy.restart_nns_and_rms(cluster)

    def validate_scaling(self, cluster, existing, additional):
        validation.validate(cluster.id)

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.EDPSparkEngine.get_supported_job_types():
            return edp_engine.EDPSparkEngine(cluster)
        if job_type in edp_engine.EDPOozieEngine.get_supported_job_types():
            return edp_engine.EDPOozieEngine(cluster)
        return None

    def get_edp_job_types(self, versions=None):
        res = {}
        for version in self.get_versions():
            if not versions or version in versions:
                oozie_engine = edp_engine.EDPOozieEngine
                spark_engine = edp_engine.EDPSparkEngine
                res[version] = (oozie_engine.get_supported_job_types() +
                                spark_engine.get_supported_job_types())
        return res

    def get_edp_config_hints(self, job_type, version):
        if job_type in edp_engine.EDPSparkEngine.get_supported_job_types():
            return edp_engine.EDPSparkEngine.get_possible_job_config(job_type)
        if job_type in edp_engine.EDPOozieEngine.get_supported_job_types():
            return edp_engine.EDPOozieEngine.get_possible_job_config(job_type)

    def get_open_ports(self, node_group):
        ports_map = {
            p_common.AMBARI_SERVER: [8080],
            p_common.APP_TIMELINE_SERVER: [8188, 8190, 10200],
            p_common.DATANODE: [50075, 50475],
            p_common.DRPC_SERVER: [3772, 3773],
            p_common.FALCON_SERVER: [15000],
            p_common.FLUME_HANDLER: [8020, 41414],
            p_common.HBASE_MASTER: [60000, 60010],
            p_common.HBASE_REGIONSERVER: [60020, 60030],
            p_common.HISTORYSERVER: [10020, 19888],
            p_common.HIVE_METASTORE: [9933],
            p_common.HIVE_SERVER: [9999, 10000],
            p_common.KAFKA_BROKER: [6667],
            p_common.NAMENODE: [8020, 9000, 50070, 50470],
            p_common.NIMBUS: [6627],
            p_common.NODEMANAGER: [8042, 8044, 45454],
            p_common.OOZIE_SERVER: [11000, 11443],
            p_common.RANGER_ADMIN: [6080],
            p_common.RESOURCEMANAGER: [8025, 8030, 8050, 8088, 8141],
            p_common.SECONDARY_NAMENODE: [50090],
            p_common.SPARK_JOBHISTORYSERVER: [18080],
            p_common.STORM_UI_SERVER: [8000, 8080, 8744],
            p_common.ZOOKEEPER_SERVER: [2181],
        }
        ports = []
        for service in node_group.node_processes:
            ports.extend(ports_map.get(service, []))
        return ports

    def get_health_checks(self, cluster):
        return health.get_health_checks(cluster)
