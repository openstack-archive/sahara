# Copyright (c) 2015 Intel Corporation
# Copyright (c) 2015 ISPRAS
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
from sahara.plugins.cdh import db_helper
from sahara.plugins.cdh.v5_4_0 import cloudera_utils as cu
from sahara.plugins.cdh.v5_4_0 import config_helper as c_helper
from sahara.plugins.cdh.v5_4_0 import deploy as dp
from sahara.plugins.cdh.v5_4_0 import edp_engine
from sahara.plugins.cdh.v5_4_0 import validation as vl


conductor = conductor.API
CU = cu.ClouderaUtilsV540()


class VersionHandler(avm.AbstractVersionHandler):

    def get_plugin_configs(self):
        return c_helper.get_plugin_configs()

    def get_node_processes(self):
        return {
            "CLOUDERA": ['CLOUDERA_MANAGER'],
            "HDFS": [],
            "NAMENODE": ['HDFS_NAMENODE'],
            "DATANODE": ['HDFS_DATANODE'],
            "SECONDARYNAMENODE": ['HDFS_SECONDARYNAMENODE'],
            "YARN": [],
            "RESOURCEMANAGER": ['YARN_RESOURCEMANAGER'],
            "NODEMANAGER": ['YARN_NODEMANAGER'],
            "JOBHISTORY": ['YARN_JOBHISTORY'],
            "OOZIE": ['OOZIE_SERVER'],
            "HIVE": [],
            "HIVESERVER": ['HIVE_SERVER2'],
            "HIVEMETASTORE": ['HIVE_METASTORE'],
            "WEBHCAT": ['HIVE_WEBHCAT'],
            "HUE": ['HUE_SERVER'],
            "SPARK_ON_YARN": ['SPARK_YARN_HISTORY_SERVER'],
            "ZOOKEEPER": ['ZOOKEEPER_SERVER'],
            "HBASE": [],
            "MASTER": ['HBASE_MASTER'],
            "REGIONSERVER": ['HBASE_REGIONSERVER'],
            "FLUME": ['FLUME_AGENT'],
            "IMPALA": [],
            "CATALOGSERVER": ['IMPALA_CATALOGSERVER'],
            "STATESTORE": ['IMPALA_STATESTORE'],
            "IMPALAD": ['IMPALAD'],
            "KS_INDEXER": ['KEY_VALUE_STORE_INDEXER'],
            "SOLR": ['SOLR_SERVER'],
            "SQOOP": ['SQOOP_SERVER'],
            "SENTRY": ['SENTRY_SERVER'],
            "KMS": ['KMS'],
            "YARN_GATEWAY": [],
            "HDFS_GATEWAY": []
        }

    def validate(self, cluster):
        vl.validate_cluster_creating(cluster)

    def configure_cluster(self, cluster):
        dp.configure_cluster(cluster)

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
        mng = CU.pu.get_manager(cluster)
        info = {
            'Cloudera Manager': {
                'Web UI': 'http://%s:7180' % mng.management_ip,
                'Username': 'admin',
                'Password': db_helper.get_cm_password(cluster)
            }
        }
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
        if job_type in edp_engine.EdpSparkEngine.get_supported_job_types():
            return edp_engine.EdpSparkEngine(cluster)
        return None

    def get_edp_job_types(self):
        return (edp_engine.EdpOozieEngine.get_supported_job_types() +
                edp_engine.EdpSparkEngine.get_supported_job_types())

    def get_edp_config_hints(self, job_type):
        return edp_engine.EdpOozieEngine.get_possible_job_config(job_type)

    def get_open_ports(self, node_group):
        return dp.get_open_ports(node_group)
