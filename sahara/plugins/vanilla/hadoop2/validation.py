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

from sahara.i18n import _
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.plugins.vanilla.hadoop2 import config_helper as cu
from sahara.plugins.vanilla import utils as vu
from sahara.utils import general as gu


def validate_cluster_creating(pctx, cluster):
    nn_count = _get_inst_count(cluster, 'namenode')
    if nn_count != 1:
        raise ex.InvalidComponentCountException('namenode', 1, nn_count)

    snn_count = _get_inst_count(cluster, 'secondarynamenode')
    if snn_count > 1:
        raise ex.InvalidComponentCountException('secondarynamenode',
                                                _('0 or 1'), snn_count)

    rm_count = _get_inst_count(cluster, 'resourcemanager')
    if rm_count > 1:
        raise ex.InvalidComponentCountException('resourcemanager', _('0 or 1'),
                                                rm_count)

    hs_count = _get_inst_count(cluster, 'historyserver')
    if hs_count > 1:
        raise ex.InvalidComponentCountException('historyserver', _('0 or 1'),
                                                hs_count)

    nm_count = _get_inst_count(cluster, 'nodemanager')
    if rm_count == 0:
        if nm_count > 0:
            raise ex.RequiredServiceMissingException('resourcemanager',
                                                     required_by='nodemanager')

    oo_count = _get_inst_count(cluster, 'oozie')
    dn_count = _get_inst_count(cluster, 'datanode')
    if oo_count > 1:
        raise ex.InvalidComponentCountException('oozie', _('0 or 1'), oo_count)

    if oo_count == 1:
        if dn_count < 1:
            raise ex.RequiredServiceMissingException('datanode',
                                                     required_by='oozie')

        if nm_count < 1:
            raise ex.RequiredServiceMissingException('nodemanager',
                                                     required_by='oozie')

        if hs_count != 1:
            raise ex.RequiredServiceMissingException('historyserver',
                                                     required_by='oozie')

    spark_hist_count = _get_inst_count(cluster, 'spark history server')
    if spark_hist_count > 1:
        raise ex.InvalidComponentCountException('spark history server',
                                                _('0 or 1'),
                                                spark_hist_count)

    rep_factor = cu.get_config_value(pctx, 'HDFS', 'dfs.replication', cluster)
    if dn_count < rep_factor:
        raise ex.InvalidComponentCountException(
            'datanode', rep_factor, dn_count, _('Number of datanodes must be '
                                                'not less than '
                                                'dfs.replication.'))

    hive_count = _get_inst_count(cluster, 'hiveserver')
    if hive_count > 1:
        raise ex.InvalidComponentCountException('hive', _('0 or 1'),
                                                hive_count)


def validate_additional_ng_scaling(cluster, additional):
    rm = vu.get_resourcemanager(cluster)
    scalable_processes = _get_scalable_processes()

    for ng_id in additional:
        ng = gu.get_by_id(cluster.node_groups, ng_id)
        if not set(ng.node_processes).issubset(scalable_processes):
            msg = _("Vanilla plugin cannot scale nodegroup with processes: %s")
            raise ex.NodeGroupCannotBeScaled(ng.name,
                                             msg % ' '.join(ng.node_processes))

        if not rm and 'nodemanager' in ng.node_processes:
            msg = _("Vanilla plugin cannot scale node group with processes "
                    "which have no master-processes run in cluster")
            raise ex.NodeGroupCannotBeScaled(ng.name, msg)


def validate_existing_ng_scaling(pctx, cluster, existing):
    scalable_processes = _get_scalable_processes()
    dn_to_delete = 0
    for ng in cluster.node_groups:
        if ng.id in existing:
            if ng.count > existing[ng.id] and "datanode" in ng.node_processes:
                dn_to_delete += ng.count - existing[ng.id]

            if not set(ng.node_processes).issubset(scalable_processes):
                msg = _("Vanilla plugin cannot scale nodegroup "
                        "with processes: %s")
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, msg % ' '.join(ng.node_processes))

    dn_amount = len(vu.get_datanodes(cluster))
    rep_factor = cu.get_config_value(pctx, 'HDFS', 'dfs.replication', cluster)

    if dn_to_delete > 0 and dn_amount - dn_to_delete < rep_factor:
        msg = _("Vanilla plugin cannot shrink cluster because it would be "
                "not enough nodes for replicas (replication factor is %s)")
        raise ex.ClusterCannotBeScaled(
            cluster.name, msg % rep_factor)


def _get_scalable_processes():
    return ['datanode', 'nodemanager']


def _get_inst_count(cluster, process):
    return sum([ng.count for ng in u.get_node_groups(cluster, process)])
