# Copyright (c) 2016 Mirantis Inc.
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
from sahara.plugins.cdh import commands as cmd
from sahara.plugins.cdh import deploy as common_deploy
from sahara.plugins.cdh.v5_11_0 import cloudera_utils as cu
from sahara.plugins import utils as gu
from sahara.service.edp import hdfs_helper as h
from sahara.utils import cluster_progress_ops as cpo

CU = cu.ClouderaUtilsV5110()

PACKAGES = common_deploy.PACKAGES


def configure_cluster(cluster):
    instances = gu.get_instances(cluster)

    if not cmd.is_pre_installed_cdh(CU.pu.get_manager(cluster).remote()):
        CU.pu.configure_os(instances)
        CU.pu.install_packages(instances, PACKAGES)

    CU.pu.start_cloudera_agents(instances)
    CU.pu.start_cloudera_manager(cluster)
    CU.update_cloudera_password(cluster)
    CU.configure_rack_awareness(cluster)
    CU.await_agents(cluster, instances)
    CU.create_mgmt_service(cluster)
    CU.create_services(cluster)
    CU.configure_services(cluster)
    CU.configure_instances(instances, cluster)
    CU.deploy_configs(cluster)


@cpo.event_wrapper(
    True, step=_("Start roles: NODEMANAGER, DATANODE"), param=('cluster', 0))
def _start_roles(cluster, instances):
    for instance in instances:
        if 'HDFS_DATANODE' in instance.node_group.node_processes:
            hdfs = CU.get_service_by_role('DATANODE', instance=instance)
            CU.start_roles(hdfs, CU.pu.get_role_name(instance, 'DATANODE'))

        if 'YARN_NODEMANAGER' in instance.node_group.node_processes:
            yarn = CU.get_service_by_role('NODEMANAGER', instance=instance)
            CU.start_roles(yarn, CU.pu.get_role_name(instance, 'NODEMANAGER'))


def scale_cluster(cluster, instances):
    if not instances:
        return

    if not cmd.is_pre_installed_cdh(instances[0].remote()):
        CU.pu.configure_os(instances)
        CU.pu.install_packages(instances, PACKAGES)

    CU.pu.start_cloudera_agents(instances)
    CU.await_agents(cluster, instances)
    CU.configure_rack_awareness(cluster)
    CU.configure_instances(instances, cluster)
    CU.update_configs(instances)
    common_deploy.prepare_scaling_kerberized_cluster(
        cluster, CU, instances)

    CU.pu.configure_swift(cluster, instances)
    _start_roles(cluster, instances)
    CU.refresh_datanodes(cluster)
    CU.refresh_yarn_nodes(cluster)
    CU.restart_stale_services(cluster)


def decommission_cluster(cluster, instances):
    dns = []
    dns_to_delete = []
    nms = []
    nms_to_delete = []
    for i in instances:
        if 'HDFS_DATANODE' in i.node_group.node_processes:
            dns.append(CU.pu.get_role_name(i, 'DATANODE'))
            dns_to_delete.append(
                CU.pu.get_role_name(i, 'HDFS_GATEWAY'))

        if 'YARN_NODEMANAGER' in i.node_group.node_processes:
            nms.append(CU.pu.get_role_name(i, 'NODEMANAGER'))
            nms_to_delete.append(
                CU.pu.get_role_name(i, 'YARN_GATEWAY'))

    if dns:
        CU.decommission_nodes(
            cluster, 'DATANODE', dns, dns_to_delete)

    if nms:
        CU.decommission_nodes(
            cluster, 'NODEMANAGER', nms, nms_to_delete)

    CU.delete_instances(cluster, instances)

    CU.refresh_datanodes(cluster)
    CU.refresh_yarn_nodes(cluster)
    CU.restart_stale_services(cluster)


@cpo.event_wrapper(True, step=_("Prepare cluster"), param=('cluster', 0))
def _prepare_cluster(cluster):
    if CU.pu.get_oozie(cluster):
        CU.pu.install_extjs(cluster)

    if CU.pu.get_hive_metastore(cluster):
        CU.pu.configure_hive(cluster)

    if CU.pu.get_sentry(cluster):
        CU.pu.configure_sentry(cluster)


@cpo.event_wrapper(
    True, step=_("Finish cluster starting"), param=('cluster', 0))
def _finish_cluster_starting(cluster):
    if CU.pu.get_hive_metastore(cluster):
        CU.pu.put_hive_hdfs_xml(cluster)

    server = CU.pu.get_hbase_master(cluster)
    if CU.pu.c_helper.is_hbase_common_lib_enabled(cluster) and server:
        with server.remote() as r:
            h.create_hbase_common_lib(r)

    if CU.pu.get_flumes(cluster):
        flume = CU.get_service_by_role('AGENT', cluster)
        CU.start_service(flume)


def start_cluster(cluster):
    _prepare_cluster(cluster)

    CU.first_run(cluster)

    CU.pu.configure_swift(cluster)

    if len(CU.pu.get_jns(cluster)) > 0:
        CU.enable_namenode_ha(cluster)
        # updating configs for NameNode role on needed nodes
        CU.update_role_config(CU.pu.get_secondarynamenode(cluster),
                              'HDFS_NAMENODE')

    if CU.pu.get_stdb_rm(cluster):
        CU.enable_resourcemanager_ha(cluster)
        # updating configs for ResourceManager on needed nodes
        CU.update_role_config(CU.pu.get_stdb_rm(cluster), 'YARN_STANDBYRM')

    _finish_cluster_starting(cluster)

    common_deploy.setup_kerberos_for_cluster(cluster, CU)


def get_open_ports(node_group):
    ports = common_deploy.get_open_ports(node_group)
    return ports
