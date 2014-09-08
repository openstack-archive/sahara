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

from oslo.config import cfg

from sahara import conductor
from sahara import context
from sahara.openstack.common import log as logging
from sahara.plugins.general import utils
from sahara.plugins.vanilla import abstractversionhandler as avm
from sahara.plugins.vanilla.hadoop2 import config as c
from sahara.plugins.vanilla.hadoop2 import edp_engine
from sahara.plugins.vanilla.hadoop2 import run_scripts as run
from sahara.plugins.vanilla.hadoop2 import scaling as sc
from sahara.plugins.vanilla.hadoop2 import validation as vl
from sahara.plugins.vanilla import utils as vu
from sahara.plugins.vanilla.v2_4_1 import config_helper as c_helper


conductor = conductor.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class VersionHandler(avm.AbstractVersionHandler):
    def __init__(self):
        self.pctx = {
            'env_confs': c_helper.get_env_configs(),
            'all_confs': c_helper.get_plugin_configs()
        }

    def get_plugin_configs(self):
        return self.pctx['all_confs']

    def get_node_processes(self):
        return {
            "Hadoop": [],
            "MapReduce": ["historyserver"],
            "HDFS": ["namenode", "datanode", "secondarynamenode"],
            "YARN": ["resourcemanager", "nodemanager"],
            "JobFlow": ["oozie"]
        }

    def validate(self, cluster):
        vl.validate_cluster_creating(self.pctx, cluster)

    def update_infra(self, cluster):
        pass

    def configure_cluster(self, cluster):
        c.configure_cluster(self.pctx, cluster)

    def start_cluster(self, cluster):
        nn = vu.get_namenode(cluster)
        run.format_namenode(nn)
        run.start_hadoop_process(nn, 'namenode')

        for snn in vu.get_secondarynamenodes(cluster):
            run.start_hadoop_process(snn, 'secondarynamenode')

        rm = vu.get_resourcemanager(cluster)
        if rm:
            run.start_yarn_process(rm, 'resourcemanager')

        run.start_all_processes(utils.get_instances(cluster),
                                ['datanode', 'nodemanager'])

        run.await_datanodes(cluster)

        hs = vu.get_historyserver(cluster)
        if hs:
            run.start_historyserver(hs)

        oo = vu.get_oozie(cluster)
        if oo:
            run.start_oozie_process(self.pctx, oo)

        self._set_cluster_info(cluster)

    def decommission_nodes(self, cluster, instances):
        sc.decommission_nodes(self.pctx, cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        vl.validate_additional_ng_scaling(cluster, additional)
        vl.validate_existing_ng_scaling(self.pctx, cluster, existing)

    def scale_cluster(self, cluster, instances):
        sc.scale_cluster(self.pctx, cluster, instances)

    def _set_cluster_info(self, cluster):
        nn = vu.get_namenode(cluster)
        rm = vu.get_resourcemanager(cluster)
        hs = vu.get_historyserver(cluster)
        oo = vu.get_oozie(cluster)

        info = {}

        if rm:
            info['YARN'] = {
                'Web UI': 'http://%s:%s' % (rm.management_ip, '8088'),
                'ResourceManager': 'http://%s:%s' % (rm.management_ip, '8032')
            }

        if nn:
            info['HDFS'] = {
                'Web UI': 'http://%s:%s' % (nn.management_ip, '50070'),
                'NameNode': 'hdfs://%s:%s' % (nn.hostname(), '9000')
            }

        if oo:
            info['JobFlow'] = {
                'Oozie': 'http://%s:%s' % (oo.management_ip, '11000')
            }

        if hs:
            info['MapReduce JobHistory Server'] = {
                'Web UI': 'http://%s:%s' % (hs.management_ip, '19888')
            }

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.EdpOozieEngine.get_supported_job_types():
            return edp_engine.EdpOozieEngine(cluster)
        return None

    def get_open_ports(self, node_group):
        return c.get_open_ports(node_group)
