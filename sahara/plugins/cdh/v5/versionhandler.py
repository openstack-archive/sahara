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
from sahara.plugins.cdh import abstractversionhandler as avm
from sahara.plugins.cdh.v5 import cloudera_utils as cu
from sahara.plugins.cdh.v5 import config_helper as c_helper
from sahara.plugins.cdh.v5 import deploy as dp
from sahara.plugins.cdh.v5 import edp_engine
from sahara.plugins.cdh.v5 import plugin_utils as pu
from sahara.plugins.cdh.v5 import validation


conductor = conductor.API
CU = cu.ClouderaUtilsV5()
PU = pu.PluginUtilsV5()
vl = validation.ValidatorV5


class VersionHandler(avm.AbstractVersionHandler):

    def get_plugin_configs(self):
        return c_helper.get_plugin_configs()

    def get_node_processes(self):
        return {
            "CLOUDERA": ['CLOUDERA_MANAGER'],
            "HDFS": ['HDFS_NAMENODE', 'HDFS_DATANODE',
                     'HDFS_SECONDARYNAMENODE'],
            "YARN": ['YARN_RESOURCEMANAGER', 'YARN_NODEMANAGER',
                     'YARN_JOBHISTORY'],
            "OOZIE": ['OOZIE_SERVER'],
            "HIVE": ['HIVE_SERVER2', 'HIVE_METASTORE', 'HIVE_WEBHCAT'],
            "HUE": ['HUE_SERVER'],
            "SPARK_ON_YARN": ['SPARK_YARN_HISTORY_SERVER'],
            "ZOOKEEPER": ['ZOOKEEPER_SERVER'],
            "HBASE": ['HBASE_MASTER', 'HBASE_REGIONSERVER'],
            "YARN_GATEWAY": [],
            "HDFS_GATEWAY": []
        }

    def validate(self, cluster):
        vl.validate_cluster_creating(cluster)

    def configure_cluster(self, cluster):
        dp.configure_cluster(cluster)
        conductor.cluster_update(
            context.ctx(), cluster, {
                'info': CU.get_cloudera_manager_info(cluster)})

    def start_cluster(self, cluster):
        dp.start_cluster(cluster)

        self._set_cluster_info(cluster)

    def decommission_nodes(self, cluster, instances):
        dp.decommission_cluster(cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        vl.validate_existing_ng_scaling(cluster, existing)
        vl.validate_additional_ng_scaling(cluster, additional)

    def scale_cluster(self, cluster, instances):
        dp.scale_cluster(cluster, instances)

    def _set_cluster_info(self, cluster):
        info = CU.get_cloudera_manager_info(cluster)
        hue = CU.pu.get_hue(cluster)
        if hue:
            info['Hue Dashboard'] = {
                'Web UI': 'http://%s:8888' % hue.management_ip
            }

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.EdpOozieEngine.get_supported_job_types():
            return edp_engine.EdpOozieEngine(cluster)
        return None

    def get_edp_job_types(self):
        return edp_engine.EdpOozieEngine.get_supported_job_types()

    def get_edp_config_hints(self, job_type):
        return edp_engine.EdpOozieEngine.get_possible_job_config(job_type)

    def get_open_ports(self, node_group):
        return dp.get_open_ports(node_group)

    def recommend_configs(self, cluster, scaling):
        PU.recommend_configs(cluster, self.get_plugin_configs(), scaling)
