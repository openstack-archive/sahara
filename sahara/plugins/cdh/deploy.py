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

import os
import telnetlib

from oslo.utils import timeutils
import six

from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.openstack.common import log as logging
from sahara.plugins.cdh import cloudera_utils as cu
from sahara.plugins.cdh import commands as cmd
from sahara.plugins.cdh import config_helper as c_helper
from sahara.plugins.cdh import db_helper
from sahara.plugins.cdh import utils as pu
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as gu
from sahara.swift import swift_helper
from sahara.utils import edp as edp_u
from sahara.utils import xmlutils

CM_API_PORT = 7180

HDFS_SERVICE_TYPE = 'HDFS'
YARN_SERVICE_TYPE = 'YARN'
OOZIE_SERVICE_TYPE = 'OOZIE'
HIVE_SERVICE_TYPE = 'HIVE'
HUE_SERVICE_TYPE = 'HUE'
SPARK_SERVICE_TYPE = 'SPARK_ON_YARN'
ZOOKEEPER_SERVICE_TYPE = 'ZOOKEEPER'
HBASE_SERVICE_TYPE = 'HBASE'

PATH_TO_CORE_SITE_XML = '/etc/hadoop/conf/core-site.xml'
HADOOP_LIB_DIR = '/usr/lib/hadoop-mapreduce'

PACKAGES = [
    'cloudera-manager-agent',
    'cloudera-manager-daemons',
    'cloudera-manager-server',
    'cloudera-manager-server-db-2',
    'hadoop-hdfs-datanode',
    'hadoop-hdfs-namenode',
    'hadoop-hdfs-secondarynamenode',
    'hadoop-mapreduce',
    'hadoop-mapreduce-historyserver',
    'hadoop-yarn-nodemanager',
    'hadoop-yarn-resourcemanager',
    'hive-metastore',
    'hive-server2',
    'hue',
    'ntp',
    'oozie',
    'oracle-j2sdk1.7',
    'spark-history-server',
    'unzip',
    'zookeeper',
    'hbase'
]

LOG = logging.getLogger(__name__)


def _merge_dicts(a, b):
    res = {}

    def update(cfg):
        for service, configs in six.iteritems(cfg):
            if not res.get(service):
                res[service] = {}

            res[service].update(configs)

    update(a)
    update(b)
    return res


def _get_configs(service, cluster=None, node_group=None):
    def get_hadoop_dirs(mount_points, suffix):
        return ','.join([x + suffix for x in mount_points])

    all_confs = {
        'OOZIE': {
            'mapreduce_yarn_service': cu.YARN_SERVICE_NAME
        },
        'YARN': {
            'hdfs_service': cu.HDFS_SERVICE_NAME
        },
        'HUE': {
            'hive_service': cu.HIVE_SERVICE_NAME,
            'oozie_service': cu.OOZIE_SERVICE_NAME
        },
        'SPARK_ON_YARN': {
            'yarn_service': cu.YARN_SERVICE_NAME
        },
        'HBASE': {
            'hdfs_service': cu.HDFS_SERVICE_NAME,
            'zookeeper_service': cu.ZOOKEEPER_SERVICE_NAME
        }
    }

    if node_group:
        paths = node_group.storage_paths()

        ng_default_confs = {
            'NAMENODE': {
                'dfs_name_dir_list': get_hadoop_dirs(paths, '/fs/nn')
            },
            'SECONDARYNAMENODE': {
                'fs_checkpoint_dir_list': get_hadoop_dirs(paths, '/fs/snn')
            },
            'DATANODE': {
                'dfs_data_dir_list': get_hadoop_dirs(paths, '/fs/dn')
            },
            'NODEMANAGER': {
                'yarn_nodemanager_local_dirs': get_hadoop_dirs(paths,
                                                               '/yarn/local')
            }
        }

        ng_user_confs = pu.convert_process_configs(node_group.node_configs)
        all_confs = _merge_dicts(all_confs, ng_user_confs)
        all_confs = _merge_dicts(all_confs, ng_default_confs)

    if cluster:
        hive_confs = {
            'HIVE': {
                'hive_metastore_database_type': 'postgresql',
                'hive_metastore_database_host':
                pu.get_manager(cluster).internal_ip,
                'hive_metastore_database_port': '7432',
                'hive_metastore_database_password':
                db_helper.get_hive_db_password(cluster),
                'mapreduce_yarn_service': cu.YARN_SERVICE_NAME
            }
        }
        hue_confs = {
            'HUE': {
                'hue_webhdfs': cu.get_role_name(pu.get_namenode(cluster),
                                                'NAMENODE')
            }
        }

        all_confs = _merge_dicts(all_confs, hue_confs)
        all_confs = _merge_dicts(all_confs, hive_confs)
        all_confs = _merge_dicts(all_confs, cluster.cluster_configs)

    return all_confs.get(service, {})


def configure_cluster(cluster):
    instances = gu.get_instances(cluster)

    if not cmd.is_pre_installed_cdh(pu.get_manager(cluster).remote()):
        _configure_os(instances)
        _install_packages(instances, PACKAGES)

    _start_cloudera_agents(instances)
    _start_cloudera_manager(cluster)
    _await_agents(instances)
    _configure_manager(cluster)
    _create_services(cluster)
    _configure_services(cluster)
    _configure_instances(instances)
    cu.deploy_configs(cluster)
    if c_helper.is_swift_enabled(cluster):
        _configure_swift(instances)


def scale_cluster(cluster, instances):
    if not instances:
        return

    if not cmd.is_pre_installed_cdh(instances[0].remote()):
        _configure_os(instances)
        _install_packages(instances, PACKAGES)

    _start_cloudera_agents(instances)
    _await_agents(instances)
    for instance in instances:
        _configure_instance(instance)
        cu.update_configs(instance)

        if 'DATANODE' in instance.node_group.node_processes:
            cu.refresh_nodes(cluster, 'DATANODE', cu.HDFS_SERVICE_NAME)

        _configure_swift_to_inst(instance)

        if 'DATANODE' in instance.node_group.node_processes:
            hdfs = cu.get_service('DATANODE', instance=instance)
            cu.start_roles(hdfs, cu.get_role_name(instance, 'DATANODE'))

        if 'NODEMANAGER' in instance.node_group.node_processes:
            yarn = cu.get_service('NODEMANAGER', instance=instance)
            cu.start_roles(yarn, cu.get_role_name(instance, 'NODEMANAGER'))


def decommission_cluster(cluster, instances):
    dns = []
    nms = []
    for i in instances:
        if 'DATANODE' in i.node_group.node_processes:
            dns.append(cu.get_role_name(i, 'DATANODE'))
        if 'NODEMANAGER' in i.node_group.node_processes:
            nms.append(cu.get_role_name(i, 'NODEMANAGER'))

    if dns:
        cu.decommission_nodes(cluster, 'DATANODE', dns)

    if nms:
        cu.decommission_nodes(cluster, 'NODEMANAGER', nms)

    cu.delete_instances(cluster, instances)

    cu.refresh_nodes(cluster, 'DATANODE', cu.HDFS_SERVICE_NAME)
    cu.refresh_nodes(cluster, 'NODEMANAGER', cu.YARN_SERVICE_NAME)


def _configure_os(instances):
    with context.ThreadGroup() as tg:
        for inst in instances:
            tg.spawn('cdh-repo-conf-%s' % inst.instance_name,
                     _configure_repo_from_inst, inst)


def _configure_repo_from_inst(instance):
    LOG.debug("Configure repos from instance '%(instance)s'" % {
        'instance': instance.instance_name})
    cluster = instance.node_group.cluster

    cdh5_repo = c_helper.get_cdh5_repo_url(cluster)
    cdh5_key = c_helper.get_cdh5_key_url(cluster)
    cm5_repo = c_helper.get_cm5_repo_url(cluster)
    cm5_key = c_helper.get_cm5_key_url(cluster)

    with instance.remote() as r:
        if cmd.is_ubuntu_os(r):
            cdh5_repo = cdh5_repo or c_helper.DEFAULT_CDH5_UBUNTU_REPO_LIST_URL
            cdh5_key = cdh5_key or c_helper.DEFAULT_CDH5_UBUNTU_REPO_KEY_URL
            cm5_repo = cm5_repo or c_helper.DEFAULT_CM5_UBUNTU_REPO_LIST_URL
            cm5_key = cm5_key or c_helper.DEFAULT_CM5_UBUNTU_REPO_KEY_URL

            cmd.add_ubuntu_repository(r, cdh5_repo, 'cdh')
            cmd.add_apt_key(r, cdh5_key)
            cmd.add_ubuntu_repository(r, cm5_repo, 'cm')
            cmd.add_apt_key(r, cm5_key)
            cmd.update_repository(r)

        if cmd.is_centos_os(r):
            cdh5_repo = cdh5_repo or c_helper.DEFAULT_CDH5_CENTOS_REPO_LIST_URL
            cm5_repo = cm5_repo or c_helper.DEFAULT_CM5_CENTOS_REPO_LIST_URL

            cmd.add_centos_repository(r, cdh5_repo, 'cdh')
            cmd.add_centos_repository(r, cm5_repo, 'cm')


def _install_packages(instances, packages):
    with context.ThreadGroup() as tg:
        for i in instances:
            tg.spawn('cdh-inst-pkgs-%s' % i.instance_name,
                     _install_pkgs, i, packages)


def _install_pkgs(instance, packages):
    with instance.remote() as r:
        cmd.install_packages(r, packages)


def _start_cloudera_agents(instances):
    with context.ThreadGroup() as tg:
        for i in instances:
            tg.spawn('cdh-agent-start-%s' % i.instance_name,
                     _start_cloudera_agent, i)


def _await_agents(instances):
    api = cu.get_api_client(instances[0].node_group.cluster)
    timeout = 300
    LOG.debug("Waiting %(timeout)s seconds for agent connected to manager" % {
        'timeout': timeout})
    s_time = timeutils.utcnow()
    while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
        hostnames = [i.fqdn() for i in instances]
        hostnames_to_manager = [h.hostname for h in api.get_all_hosts('full')]
        is_ok = True
        for hostname in hostnames:
            if hostname not in hostnames_to_manager:
                is_ok = False
                break

        if not is_ok:
            context.sleep(5)
        else:
            break
    else:
        raise ex.HadoopProvisionError(_("Cloudera agents failed to connect to"
                                        " Cloudera Manager"))


def _start_cloudera_agent(instance):
    mng_hostname = pu.get_manager(instance.node_group.cluster).hostname()
    with instance.remote() as r:
        cmd.start_ntp(r)
        cmd.configure_agent(r, mng_hostname)
        cmd.start_agent(r)


def _start_cloudera_manager(cluster):
    manager = pu.get_manager(cluster)
    with manager.remote() as r:
        cmd.start_cloudera_db(r)
        cmd.start_manager(r)

    timeout = 300
    LOG.debug("Waiting %(timeout)s seconds for Manager to start : " % {
        'timeout': timeout})
    s_time = timeutils.utcnow()
    while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
        try:
            conn = telnetlib.Telnet(manager.management_ip, CM_API_PORT)
            conn.close()
            break
        except IOError:
            context.sleep(2)
    else:
        message = _("Cloudera Manager failed to start in %(timeout)s minutes "
                    "on node '%(node)s' of cluster '%(cluster)s'") % {
                        'timeout': timeout / 60,
                        'node': manager.management_ip,
                        'cluster': cluster.name}
        raise ex.HadoopProvisionError(message)

    LOG.info(_LI("Cloudera Manager has been started"))


def _create_services(cluster):
    api = cu.get_api_client(cluster)

    fullversion = ('5.0.0' if cluster.hadoop_version == '5'
                   else cluster.hadoop_version)
    cm_cluster = api.create_cluster(cluster.name,
                                    fullVersion=fullversion)

    if len(pu.get_zookeepers(cluster)) > 0:
        cm_cluster.create_service(cu.ZOOKEEPER_SERVICE_NAME,
                                  ZOOKEEPER_SERVICE_TYPE)
    cm_cluster.create_service(cu.HDFS_SERVICE_NAME, HDFS_SERVICE_TYPE)
    cm_cluster.create_service(cu.YARN_SERVICE_NAME, YARN_SERVICE_TYPE)
    cm_cluster.create_service(cu.OOZIE_SERVICE_NAME, OOZIE_SERVICE_TYPE)
    if pu.get_hive_metastore(cluster):
        cm_cluster.create_service(cu.HIVE_SERVICE_NAME, HIVE_SERVICE_TYPE)
    if pu.get_hue(cluster):
        cm_cluster.create_service(cu.HUE_SERVICE_NAME, HUE_SERVICE_TYPE)
    if pu.get_spark_historyserver(cluster):
        cm_cluster.create_service(cu.SPARK_SERVICE_NAME, SPARK_SERVICE_TYPE)
    if pu.get_hbase_master(cluster):
        cm_cluster.create_service(cu.HBASE_SERVICE_NAME, HBASE_SERVICE_TYPE)


def _configure_services(cluster):
    cm_cluster = cu.get_cloudera_cluster(cluster)

    if len(pu.get_zookeepers(cluster)) > 0:
        zookeeper = cm_cluster.get_service(cu.ZOOKEEPER_SERVICE_NAME)
        zookeeper.update_config(_get_configs(ZOOKEEPER_SERVICE_TYPE,
                                cluster=cluster))

    hdfs = cm_cluster.get_service(cu.HDFS_SERVICE_NAME)
    hdfs.update_config(_get_configs(HDFS_SERVICE_TYPE, cluster=cluster))

    yarn = cm_cluster.get_service(cu.YARN_SERVICE_NAME)
    yarn.update_config(_get_configs(YARN_SERVICE_TYPE, cluster=cluster))

    oozie = cm_cluster.get_service(cu.OOZIE_SERVICE_NAME)
    oozie.update_config(_get_configs(OOZIE_SERVICE_TYPE, cluster=cluster))

    if pu.get_hive_metastore(cluster):
        hive = cm_cluster.get_service(cu.HIVE_SERVICE_NAME)
        hive.update_config(_get_configs(HIVE_SERVICE_TYPE, cluster=cluster))

    if pu.get_hue(cluster):
        hue = cm_cluster.get_service(cu.HUE_SERVICE_NAME)
        hue.update_config(_get_configs(HUE_SERVICE_TYPE, cluster=cluster))

    if pu.get_spark_historyserver(cluster):
        spark = cm_cluster.get_service(cu.SPARK_SERVICE_NAME)
        spark.update_config(_get_configs(SPARK_SERVICE_TYPE, cluster=cluster))
    if pu.get_hbase_master(cluster):
        hbase = cm_cluster.get_service(cu.HBASE_SERVICE_NAME)
        hbase.update_config(_get_configs(HBASE_SERVICE_TYPE, cluster=cluster))


def _configure_instances(instances):
    for inst in instances:
        _configure_instance(inst)


def _configure_instance(instance):
    for process in instance.node_group.node_processes:
        _add_role(instance, process)


def _add_role(instance, process):
    if process in ['MANAGER']:
        return

    service = cu.get_service(process, instance=instance)
    role = service.create_role(cu.get_role_name(instance, process),
                               process, instance.fqdn())
    role.update_config(_get_configs(process, node_group=instance.node_group))


def _configure_manager(cluster):
    cu.create_mgmt_service(cluster)


def _configure_swift(instances):
    with context.ThreadGroup() as tg:
        for i in instances:
            tg.spawn('cdh-swift-conf-%s' % i.instance_name,
                     _configure_swift_to_inst, i)


def _configure_swift_to_inst(instance):
    cluster = instance.node_group.cluster
    with instance.remote() as r:
        r.execute_command('sudo curl %s -o %s/hadoop-openstack.jar' % (
            c_helper.get_swift_lib_url(cluster), HADOOP_LIB_DIR))
        core_site = r.read_file_from(PATH_TO_CORE_SITE_XML)
        configs = xmlutils.parse_hadoop_xml_with_name_and_value(core_site)
        configs.extend(swift_helper.get_swift_configs())
        confs = dict((c['name'], c['value']) for c in configs)
        new_core_site = xmlutils.create_hadoop_xml(confs)
        r.write_file_to(PATH_TO_CORE_SITE_XML, new_core_site, run_as_root=True)


def _put_hive_hdfs_xml(cluster):
    servers = pu.get_hive_servers(cluster)
    with servers[0].remote() as r:
        conf_path = edp_u.get_hive_shared_conf_path('hdfs')
        r.execute_command(
            'sudo su - -c "hadoop fs -mkdir -p %s" hdfs'
            % os.path.dirname(conf_path))
        r.execute_command(
            'sudo su - -c "hadoop fs -put /etc/hive/conf/hive-site.xml '
            '%s" hdfs' % conf_path)


def _configure_hive(cluster):
    manager = pu.get_manager(cluster)
    with manager.remote() as r:
        db_helper.create_hive_database(cluster, r)


def _install_extjs(cluster):
    extjs_remote_location = c_helper.get_extjs_lib_url(cluster)
    extjs_vm_location_dir = '/var/lib/oozie'
    extjs_vm_location_path = extjs_vm_location_dir + '/extjs.zip'
    with pu.get_oozie(cluster).remote() as r:
        if r.execute_command('ls %s/ext-2.2' % extjs_vm_location_dir,
                             raise_when_error=False)[0] != 0:
            r.execute_command('curl -L -o \'%s\' %s' % (
                extjs_vm_location_path,  extjs_remote_location),
                run_as_root=True)
            r.execute_command('unzip %s -d %s' % (
                extjs_vm_location_path, extjs_vm_location_dir),
                run_as_root=True)


def _clean_deploy_cc(cluster):
    # We need to disable Deploy Client Configuration in first_run.
    instances = gu.get_instances(cluster)
    for instance in instances:
        with instance.remote() as r:
            r.execute_command(
                'cp `find /usr/ -name deploy-cc.sh` cc.sh')
            r.execute_command('echo "#!/bin/bash\necho \$1" > cc1.sh')
            r.execute_command(
                'sudo cp cc1.sh `find /usr/ -name deploy-cc.sh`')


def _restore_deploy_cc(cluster):
    # Restore back the script after first_run.
    instances = gu.get_instances(cluster)
    for instance in instances:
        with instance.remote() as r:
            r.execute_command(
                'sudo cp cc.sh `find /usr/ -name deploy-cc.sh`')


def start_cluster(cluster):
    _clean_deploy_cc(cluster)

    if pu.get_oozie(cluster):
        _install_extjs(cluster)

    if pu.get_hive_metastore(cluster):
        _configure_hive(cluster)

    cu.first_run(cluster)

    if pu.get_hive_metastore(cluster):
        _put_hive_hdfs_xml(cluster)

    _restore_deploy_cc(cluster)


def get_open_ports(node_group):
    ports = [9000]  # for CM agent

    ports_map = {
        'MANAGER': [7180, 7182, 7183, 7432, 7184, 8084, 8086, 10101,
                    9997, 9996, 8087, 9998, 9999, 8085, 9995, 9994],
        'NAMENODE': [8020, 8022, 50070, 50470],
        'SECONDARYNAMENODE': [50090, 50495],
        'DATANODE': [50010, 1004, 50075, 1006, 50020],
        'RESOURCEMANAGER': [8030, 8031, 8032, 8033, 8088],
        'NODEMANAGER': [8040, 8041, 8042],
        'JOBHISTORY': [10020, 19888],
        'HIVEMETASTORE': [9083],
        'HIVESERVER2': [10000],
        'HUE_SERVER': [8888],
        'OOZIE_SERVER': [11000, 11001],
        'SPARK_YARN_HISTORY_SERVER': [18088],
        'SERVER': [2181, 3181, 4181, 9010],
        'MASTER': [60000],
        'REGIONSERVER': [60020]
    }

    for process in node_group.node_processes:
        if process in ports_map:
            ports.extend(ports_map[process])

    return ports
