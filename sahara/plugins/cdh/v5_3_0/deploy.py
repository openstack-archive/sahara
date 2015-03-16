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
from sahara.plugins.cdh import commands as cmd
from sahara.plugins.cdh.v5_3_0 import cloudera_utils as cu
from sahara.plugins import utils as gu
from sahara.service.edp import hdfs_helper as h
from sahara.utils import cluster_progress_ops as cpo

PACKAGES = [
    'cloudera-manager-agent',
    'cloudera-manager-daemons',
    'cloudera-manager-server',
    'cloudera-manager-server-db-2',
    'flume-ng',
    'hadoop-hdfs-datanode',
    'hadoop-hdfs-namenode',
    'hadoop-hdfs-secondarynamenode',
    'hadoop-mapreduce',
    'hadoop-mapreduce-historyserver',
    'hadoop-yarn-nodemanager',
    'hadoop-yarn-resourcemanager',
    'hbase',
    'hbase-solr',
    'hive-hcatalog',
    'hive-metastore',
    'hive-server2',
    'hive-webhcat-server',
    'hue',
    'impala',
    'impala-server',
    'impala-state-store',
    'impala-catalog',
    'impala-shell',
    'ntp',
    'oozie',
    'oracle-j2sdk1.7',
    'sentry',
    'solr-server',
    'solr-doc',
    'search',
    'spark-history-server',
    'sqoop2',
    'unzip',
    'zookeeper'
]

CU = cu.ClouderaUtilsV530()


def configure_cluster(cluster):
    instances = gu.get_instances(cluster)

    if not cmd.is_pre_installed_cdh(CU.pu.get_manager(cluster).remote()):
        CU.pu.configure_os(instances)
        CU.pu.install_packages(instances, PACKAGES)

    CU.pu.start_cloudera_agents(instances)
    CU.pu.start_cloudera_manager(cluster)
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
    CU.configure_instances(instances, cluster)
    CU.update_configs(instances)
    CU.pu.configure_swift(cluster, instances)
    CU.refresh_datanodes(cluster)
    _start_roles(cluster, instances)


def decommission_cluster(cluster, instances):
    dns = []
    nms = []
    for i in instances:
        if 'HDFS_DATANODE' in i.node_group.node_processes:
            dns.append(CU.pu.get_role_name(i, 'DATANODE'))
        if 'YARN_NODEMANAGER' in i.node_group.node_processes:
            nms.append(CU.pu.get_role_name(i, 'NODEMANAGER'))

    if dns:
        CU.decommission_nodes(cluster, 'DATANODE', dns)

    if nms:
        CU.decommission_nodes(cluster, 'NODEMANAGER', nms)

    CU.delete_instances(cluster, instances)

    CU.refresh_datanodes(cluster)
    CU.refresh_yarn_nodes(cluster)


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

    _finish_cluster_starting(cluster)


def get_open_ports(node_group):
    ports = [9000]  # for CM agent

    ports_map = {
        'CLOUDERA_MANAGER': [7180, 7182, 7183, 7432, 7184, 8084, 8086, 10101,
                             9997, 9996, 8087, 9998, 9999, 8085, 9995, 9994],
        'HDFS_NAMENODE': [8020, 8022, 50070, 50470],
        'HDFS_SECONDARYNAMENODE': [50090, 50495],
        'HDFS_DATANODE': [50010, 1004, 50075, 1006, 50020],
        'YARN_RESOURCEMANAGER': [8030, 8031, 8032, 8033, 8088],
        'YARN_NODEMANAGER': [8040, 8041, 8042],
        'YARN_JOBHISTORY': [10020, 19888],
        'HIVE_METASTORE': [9083],
        'HIVE_SERVER2': [10000],
        'HUE_SERVER': [8888],
        'OOZIE_SERVER': [11000, 11001],
        'SPARK_YARN_HISTORY_SERVER': [18088],
        'ZOOKEEPER_SERVER': [2181, 3181, 4181, 9010],
        'HBASE_MASTER': [60000],
        'HBASE_REGIONSERVER': [60020],
        'FLUME_AGENT': [41414],
        'SENTRY_SERVER': [8038],
        'SOLR_SERVER': [8983, 8984],
        'SQOOP_SERVER': [8005, 12000],
        'KEY_VALUE_STORE_INDEXER': [],
        'IMPALA_CATALOGSERVER': [25020, 26000],
        'IMPALA_STATESTORE': [25010, 24000],
        'IMPALAD': [21050, 21000, 23000, 25000, 28000, 22000]
    }

    for process in node_group.node_processes:
        if process in ports_map:
            ports.extend(ports_map[process])

    return ports
