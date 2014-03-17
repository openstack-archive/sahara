# Copyright (c) 2014 Intel Corporation
# Copyright (c) 2014 Mirantis, Inc.
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

from sahara.openstack.common import log as logging
from sahara.plugins.general import exceptions as ex
from sahara.plugins.general import utils as u
from sahara.plugins.intel import abstractversionhandler as avm
from sahara.plugins.intel.v2_5_1 import config_helper as c_helper
from sahara.plugins.intel.v2_5_1 import installer as ins

LOG = logging.getLogger(__name__)
conductor = conductor.API


class VersionHandler(avm.AbstractVersionHandler):

    def get_node_processes(self):
        processes = {
            "Manager": ["manager"],
            "HDFS": ["namenode", "datanode", "secondarynamenode"],
            "MapReduce": ["jobtracker", "tasktracker"],
            "Hadoop": [],
            "JobFlow": ["oozie"]
        }

        return processes

    def get_plugin_configs(self):
        return c_helper.get_plugin_configs()

    def configure_cluster(self, cluster):
        LOG.info("Configure IDH cluster")
        cluster = ins.create_hadoop_ssh_keys(cluster)
        ins.configure_os(cluster)
        ins.install_manager(cluster)
        ins.install_cluster(cluster)

    def start_cluster(self, cluster):
        LOG.info("Start IDH cluster")
        ins.start_cluster(cluster)
        self._set_cluster_info(cluster)

    def validate(self, cluster):
        nn_count = sum([ng.count for ng
                        in u.get_node_groups(cluster, 'namenode')])
        if nn_count != 1:
            raise ex.InvalidComponentCountException('namenode', 1, nn_count)

        jt_count = sum([ng.count for ng
                        in u.get_node_groups(cluster, 'jobtracker')])
        if jt_count > 1:
            raise ex.InvalidComponentCountException('jobtracker', '0 or 1',
                                                    jt_count)

        tt_count = sum([ng.count for ng
                        in u.get_node_groups(cluster, 'tasktracker')])
        if jt_count == 0 and tt_count > 0:
            raise ex.RequiredServiceMissingException(
                'jobtracker', required_by='tasktracker')

        mng_count = sum([ng.count for ng
                         in u.get_node_groups(cluster, 'manager')])
        if mng_count != 1:
            raise ex.InvalidComponentCountException('manager', 1, mng_count)

    def scale_cluster(self, cluster, instances):
        ins.configure_os_from_instances(cluster, instances)
        ins.scale_cluster(cluster, instances)

    def decommission_nodes(self, cluster, instances):
        ins.decommission_nodes(cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        self._validate_additional_ng_scaling(cluster, additional)
        self._validate_existing_ng_scaling(cluster, existing)

    def _get_scalable_processes(self):
        return ["datanode", "tasktracker"]

    def _get_by_id(self, lst, id):
        for obj in lst:
            if obj.id == id:
                return obj

    def _validate_additional_ng_scaling(self, cluster, additional):
        jt = u.get_jobtracker(cluster)
        scalable_processes = self._get_scalable_processes()

        for ng_id in additional:
            ng = self._get_by_id(cluster.node_groups, ng_id)
            if not set(ng.node_processes).issubset(scalable_processes):
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, "Intel plugin cannot scale nodegroup"
                             " with processes: " +
                             ' '.join(ng.node_processes))
            if not jt and 'tasktracker' in ng.node_processes:
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, "Intel plugin cannot scale node group with "
                             "processes which have no master-processes run "
                             "in cluster")

    def _validate_existing_ng_scaling(self, cluster, existing):
        scalable_processes = self._get_scalable_processes()
        dn_to_delete = 0
        for ng in cluster.node_groups:
            if ng.id in existing:
                if ng.count > existing[ng.id] and "datanode" in \
                        ng.node_processes:
                    dn_to_delete += ng.count - existing[ng.id]
                if not set(ng.node_processes).issubset(scalable_processes):
                    raise ex.NodeGroupCannotBeScaled(
                        ng.name, "Intel plugin cannot scale nodegroup"
                                 " with processes: " +
                                 ' '.join(ng.node_processes))

    def _set_cluster_info(self, cluster):
        mng = u.get_instances(cluster, 'manager')[0]
        nn = u.get_namenode(cluster)
        jt = u.get_jobtracker(cluster)
        oozie = u.get_oozie(cluster)

        #TODO(alazarev) make port configurable (bug #1262895)
        info = {'IDH Manager': {
            'Web UI': 'https://%s:9443' % mng.management_ip
        }}

        if jt:
            #TODO(alazarev) make port configurable (bug #1262895)
            info['MapReduce'] = {
                'Web UI': 'http://%s:50030' % jt.management_ip
            }
            #TODO(alazarev) make port configurable (bug #1262895)
            info['MapReduce']['JobTracker'] = '%s:54311' % jt.hostname()
        if nn:
            #TODO(alazarev) make port configurable (bug #1262895)
            info['HDFS'] = {
                'Web UI': 'http://%s:50070' % nn.management_ip
            }
            #TODO(alazarev) make port configurable (bug #1262895)
            info['HDFS']['NameNode'] = 'hdfs://%s:8020' % nn.hostname()

        if oozie:
            #TODO(alazarev) make port configurable (bug #1262895)
            info['JobFlow'] = {
                'Oozie': 'http://%s:11000' % oozie.management_ip
            }

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})

    def get_resource_manager_uri(self, cluster):
        return cluster['info']['MapReduce']['JobTracker']
