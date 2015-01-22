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
from sahara.i18n import _
from sahara.plugins.cdh import config_helper as c_helper
from sahara.plugins.cdh import deploy as dp
from sahara.plugins.cdh import edp_engine
from sahara.plugins.cdh import utils as cu
from sahara.plugins.cdh import validation as vl
from sahara.plugins import provisioning as p

conductor = conductor.API


class CDHPluginProvider(p.ProvisioningPluginBase):

    def get_title(self):
        return "Cloudera Plugin"

    def get_description(self):
        return _('The Cloudera Sahara plugin provides the ability to '
                 'launch the Cloudera distribution of Apache Hadoop '
                 '(CDH) with Cloudera Manager management console.')

    def get_versions(self):
        return ['5', '5.2.0', '5.3.0']

    def get_node_processes(self, hadoop_version):
        processes = {
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
            "SQOOP": ['SQOOP_SERVER']
        }
        if hadoop_version >= '5.2.0':
            processes["SENTRY"] = ['SENTRY_SERVER']
        return processes

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
        dp.decommission_cluster(cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        vl.validate_existing_ng_scaling(cluster, existing)
        vl.validate_additional_ng_scaling(cluster, additional)

    def _set_cluster_info(self, cluster):
        mng = cu.get_manager(cluster)
        info = {
            'Cloudera Manager': {
                'Web UI': 'http://%s:7180' % mng.management_ip,
                'Username': 'admin',
                'Password': 'admin'
            }
        }
        hue = cu.get_hue(cluster)
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

    def get_open_ports(self, node_group):
        return dp.get_open_ports(node_group)
