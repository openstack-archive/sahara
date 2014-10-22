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

from sahara import context
from sahara.plugins.mapr.util import cluster_helper as clh_utils
import sahara.plugins.mapr.util.config_utils as cu
import sahara.plugins.mapr.util.names as n
from sahara.plugins.mapr.util import scaling
from sahara.plugins.mapr.util import start_helper as start_helper
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.plugins.mapr.versions.base_context as bc
from sahara.plugins.mapr.versions import base_version_handler as bvh
import sahara.plugins.mapr.versions.v4_0_1_mrv2.cluster_configurer as cc


SIXTY_SECONDS = 60
WAIT_OOZIE_INTERVAL = 300


version = '4.0.1.mrv2'


class VersionHandler(bvh.BaseVersionHandler):

    def get_plugin_version(self):
        return version

    def start_cluster(self, cluster):
        start_helper.exec_configure_sh_on_cluster(
            cluster, self.get_configure_sh_string(cluster))
        start_helper.wait_for_mfs_unlock(cluster, self.get_waiting_script())
        start_helper.setup_maprfs_on_cluster(
            cluster, self.get_disk_setup_script())
        start_helper.start_zookeeper_nodes_on_cluster(cluster)
        start_helper.start_warden_on_cldb_nodes(cluster)
        context.sleep(SIXTY_SECONDS)
        start_helper.start_warden_on_other_nodes(cluster)
        start_helper.start_ecosystem(self.get_context(cluster))

    def get_cluster_configurer(self, cluster, plugin_spec):
        return cc.ClusterConfigurer(cluster, plugin_spec)

    def get_configure_sh_string(self, cluster):
        return ('/opt/mapr/server/configure.sh'
                + ' -C ' + clh_utils.get_cldb_nodes_ip(cluster)
                + ' -Z ' + clh_utils.get_zookeeper_nodes_ip(cluster)
                + ' -RM ' + clh_utils.get_resourcemanager_ip(cluster)
                + ' -HS ' + clh_utils.get_historyserver_ip(cluster) + ' -f')

    def scale_cluster(self, cluster, instances):
        scaling.scale_cluster(cluster, instances, self.get_disk_setup_script(),
                              self.get_waiting_script(),
                              self.get_context(cluster),
                              self.get_configure_sh_string(cluster), False)

    def decommission_nodes(self, cluster, instances):
        scaling.decommission_nodes(
            cluster, instances, self.get_configure_sh_string(cluster))

    def get_waiting_script(self):
        return 'plugins/mapr/util/resources/waiting_script.sh'

    def get_cluster_validation_rules(self, cluster):
        return [vu.not_less_than_count_component_vr(n.ZOOKEEPER, 1),
                vu.not_less_than_count_component_vr(n.CLDB, 1),
                vu.not_less_than_count_component_vr(n.NODE_MANAGER, 1),
                vu.not_less_than_count_component_vr(n.FILE_SERVER, 1),
                vu.not_more_than_count_component_vr(n.OOZIE, 1),
                vu.not_more_than_count_component_vr(n.WEB_SERVER, 1),
                vu.equal_count_component_vr(n.RESOURCE_MANAGER, 1),
                vu.equal_count_component_vr(n.HISTORY_SERVER, 1),
                vu.node_dependency_satisfied_vr(n.NODE_MANAGER, n.FILE_SERVER),
                vu.node_dependency_satisfied_vr(n.CLDB, n.FILE_SERVER)]

    def get_scaling_validation_rules(self):
        return []

    def get_edp_validation_rules(self):
        return []

    def get_context(self, cluster):
        return Context(cluster)


class Context(bc.BaseContext):
    m7_enabled_config = n.IS_M7_ENABLED
    hive_version_config = 'Hive Version'
    oozie_version_config = 'Oozie Version'

    def __init__(self, cluster):
        self.cluster = cluster

    def get_cluster(self):
        return self.cluster

    def is_m7_enabled(self):
        configs = cu.get_cluster_configs(self.get_cluster())
        return configs[n.GENERAL][Context.m7_enabled_config]

    def get_hadoop_version(self):
        return '2.4.1'
