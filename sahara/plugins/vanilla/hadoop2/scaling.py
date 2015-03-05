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

from oslo_utils import timeutils

from sahara import context
from sahara.i18n import _
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.plugins.vanilla.hadoop2 import config
from sahara.plugins.vanilla.hadoop2 import run_scripts as run
from sahara.plugins.vanilla.hadoop2 import utils as pu
from sahara.plugins.vanilla import utils as vu
from sahara.utils import cluster_progress_ops as cpo

HADOOP_CONF_DIR = config.HADOOP_CONF_DIR


def scale_cluster(pctx, cluster, instances):
    config.configure_instances(pctx, instances)
    _update_include_files(cluster)
    run.refresh_hadoop_nodes(cluster)
    rm = vu.get_resourcemanager(cluster)
    if rm:
        run.refresh_yarn_nodes(cluster)

    config.configure_topology_data(pctx, cluster)
    run.start_all_processes(instances, [])


def _get_instances_with_service(instances, service):
    ret = []
    for instance in instances:
        if service in instance.node_group.node_processes:
            ret.append(instance)

    return ret


@cpo.event_wrapper(True, step=_("Update include files"), param=('cluster', 0))
def _update_include_files(cluster, dec_instances=None):
    dec_instances = dec_instances or []
    dec_instances_ids = [instance.id for instance in dec_instances]

    instances = u.get_instances(cluster)

    inst_filter = lambda inst: inst.id not in dec_instances_ids

    datanodes = filter(inst_filter, vu.get_datanodes(cluster))
    nodemanagers = filter(inst_filter, vu.get_nodemanagers(cluster))
    dn_hosts = u.generate_fqdn_host_names(datanodes)
    nm_hosts = u.generate_fqdn_host_names(nodemanagers)
    for instance in instances:
        with instance.remote() as r:
            r.execute_command(
                'sudo su - -c "echo \'%s\' > %s/dn-include" hadoop' % (
                    dn_hosts, HADOOP_CONF_DIR))
            r.execute_command(
                'sudo su - -c "echo \'%s\' > %s/nm-include" hadoop' % (
                    nm_hosts, HADOOP_CONF_DIR))


def decommission_nodes(pctx, cluster, instances):
    datanodes = _get_instances_with_service(instances, 'datanode')
    nodemanagers = _get_instances_with_service(instances, 'nodemanager')
    _update_exclude_files(cluster, instances)

    run.refresh_hadoop_nodes(cluster)
    rm = vu.get_resourcemanager(cluster)
    if rm:
        run.refresh_yarn_nodes(cluster)

    _check_nodemanagers_decommission(cluster, nodemanagers)
    _check_datanodes_decommission(cluster, datanodes)

    _update_include_files(cluster, instances)
    _clear_exclude_files(cluster)
    run.refresh_hadoop_nodes(cluster)

    config.configure_topology_data(pctx, cluster)


def _update_exclude_files(cluster, instances):
    datanodes = _get_instances_with_service(instances, 'datanode')
    nodemanagers = _get_instances_with_service(instances, 'nodemanager')
    dn_hosts = u.generate_fqdn_host_names(datanodes)
    nm_hosts = u.generate_fqdn_host_names(nodemanagers)
    for instance in u.get_instances(cluster):
        with instance.remote() as r:
            r.execute_command(
                'sudo su - -c "echo \'%s\' > %s/dn-exclude" hadoop' % (
                    dn_hosts, HADOOP_CONF_DIR))
            r.execute_command(
                'sudo su - -c "echo \'%s\' > %s/nm-exclude" hadoop' % (
                    nm_hosts, HADOOP_CONF_DIR))


def _clear_exclude_files(cluster):
    for instance in u.get_instances(cluster):
        with instance.remote() as r:
            r.execute_command(
                'sudo su - -c "echo > %s/dn-exclude" hadoop' % HADOOP_CONF_DIR)
            r.execute_command(
                'sudo su - -c "echo > %s/nm-exclude" hadoop' % HADOOP_CONF_DIR)


def _check_decommission(cluster, instances, check_func, timeout):
    s_time = timeutils.utcnow()
    while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
        statuses = check_func(cluster)
        dec_ok = True
        for instance in instances:
            if statuses[instance.fqdn()] != 'decommissioned':
                dec_ok = False

        if dec_ok:
            return
        else:
            context.sleep(5)
    else:
        ex.DecommissionError(
            _("Cannot finish decommission of cluster %(cluster)s in "
              "%(seconds)d seconds") %
            {"cluster": cluster, "seconds": timeout})


@cpo.event_wrapper(
    True, step=_("Decommission %s") % "NodeManagers", param=('cluster', 0))
def _check_nodemanagers_decommission(cluster, instances):
    _check_decommission(cluster, instances, pu.get_nodemanagers_status, 300)


@cpo.event_wrapper(
    True, step=_("Decommission %s") % "DataNodes", param=('cluster', 0))
def _check_datanodes_decommission(cluster, instances):
    _check_decommission(cluster, instances, pu.get_datanodes_status, 3600 * 4)
