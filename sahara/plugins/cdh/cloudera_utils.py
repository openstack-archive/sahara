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

import functools

# cm_api client is not present in OS requirements
try:
    from cm_api import api_client
    from cm_api.endpoints import services
except ImportError:
    api_client = None
    services = None

from sahara.i18n import _
from sahara.plugins.cdh import utils as pu
from sahara.plugins import exceptions as ex

CM_DEFAULT_USERNAME = 'admin'
CM_DEFAULT_PASSWD = 'admin'
CM_API_VERSION = 7

HDFS_SERVICE_NAME = 'hdfs01'
YARN_SERVICE_NAME = 'yarn01'
OOZIE_SERVICE_NAME = 'oozie01'
HIVE_SERVICE_NAME = 'hive01'
HUE_SERVICE_NAME = 'hue01'
SPARK_SERVICE_NAME = 'spark_on_yarn01'


def have_cm_api_libs():
    return api_client and services


def cloudera_cmd(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        for cmd in f(*args, **kwargs):
            result = cmd.wait()
            if not result.success:
                raise ex.HadoopProvisionError(result.resultMessage)

    return wrapper


def get_api_client(cluster):
    manager_ip = pu.get_manager(cluster).management_ip
    return api_client.ApiResource(manager_ip, username=CM_DEFAULT_USERNAME,
                                  password=CM_DEFAULT_PASSWD,
                                  version=CM_API_VERSION)


def get_cloudera_cluster(cluster):
    api = get_api_client(cluster)
    return api.get_cluster(cluster.name)


@cloudera_cmd
def start_instances(cluster):
    cm_cluster = get_cloudera_cluster(cluster)
    yield cm_cluster.start()


def delete_instances(cluster, instances):
    api = get_api_client(cluster)
    cm_cluster = get_cloudera_cluster(cluster)
    hosts = api.get_all_hosts(view='full')
    hostsnames_to_deleted = [i.fqdn() for i in instances]
    for host in hosts:
        if host.hostname in hostsnames_to_deleted:
            cm_cluster.remove_host(host.hostId)
            api.delete_host(host.hostId)


def get_service(process, cluster=None, instance=None):
    cm_cluster = None
    if cluster:
        cm_cluster = get_cloudera_cluster(cluster)
    elif instance:
        cm_cluster = get_cloudera_cluster(instance.node_group.cluster)
    else:
        raise ValueError(_("'cluster' or 'instance' argument missed"))

    if process in ['NAMENODE', 'DATANODE', 'SECONDARYNAMENODE']:
        return cm_cluster.get_service(HDFS_SERVICE_NAME)
    elif process in ['RESOURCEMANAGER', 'NODEMANAGER', 'JOBHISTORY']:
        return cm_cluster.get_service(YARN_SERVICE_NAME)
    elif process in ['OOZIE_SERVER']:
        return cm_cluster.get_service(OOZIE_SERVICE_NAME)
    elif process in ['HIVESERVER2', 'HIVEMETASTORE', 'WEBHCAT']:
        return cm_cluster.get_service(HIVE_SERVICE_NAME)
    elif process in ['HUE_SERVER']:
        return cm_cluster.get_service(HUE_SERVICE_NAME)
    elif process in ['SPARK_YARN_HISTORY_SERVER']:
        return cm_cluster.get_service(SPARK_SERVICE_NAME)
    else:
        raise ValueError(
            _("Process %(process)s is not supported by CDH plugin") %
            {'process': process})


def decommission_nodes(cluster, process, role_names):
    service = get_service(process, cluster)
    service.decommission(*role_names).wait()
    for role_name in role_names:
        service.delete_role(role_name)


@cloudera_cmd
def refresh_nodes(cluster, process, service_name):
    cm_cluster = get_cloudera_cluster(cluster)
    service = cm_cluster.get_service(service_name)

    nds = [n.name for n in service.get_roles_by_type(process)]
    for nd in nds:
        for st in service.refresh(nd):
            yield st


@cloudera_cmd
def deploy_configs(cluster):
    cm_cluster = get_cloudera_cluster(cluster)
    yield cm_cluster.deploy_client_config()


@cloudera_cmd
def update_configs(instance):
    for process in instance.node_group.node_processes:
        service = get_service(process, instance=instance)
        yield service.deploy_client_config(get_role_name(instance, process))


def get_role_name(instance, service):
    # NOTE: role name must match regexp "[_A-Za-z][-_A-Za-z0-9]{0,63}"
    shortcuts = {
        'ALERTPUBLISHER': 'AP',
        'DATANODE': 'DN',
        'EVENTSERVER': 'ES',
        'HIVEMETASTORE': 'HVM',
        'HIVESERVER2': 'HVS',
        'HOSTMONITOR': 'HM',
        'JOBHISTORY': 'JS',
        'NAMENODE': 'NN',
        'NODEMANAGER': 'NM',
        'OOZIE_SERVER': 'OS',
        'RESOURCEMANAGER': 'RM',
        'SECONDARYNAMENODE': 'SNN',
        'SERVICEMONITOR': 'SM',
        'WEBHCAT': 'WHC',
        'SPARK_YARN_HISTORY_SERVER': 'SHS',
    }
    return '%s_%s' % (shortcuts.get(service, service),
                      instance.hostname().replace('-', '_'))


def create_mgmt_service(cluster):
    api = get_api_client(cluster)
    cm = api.get_cloudera_manager()

    setup_info = services.ApiServiceSetupInfo()
    manager = pu.get_manager(cluster)
    hostname = manager.fqdn()
    processes = ['SERVICEMONITOR', 'HOSTMONITOR',
                 'EVENTSERVER', 'ALERTPUBLISHER']
    for proc in processes:
        setup_info.add_role_info(get_role_name(manager, proc), proc, hostname)

    cm.create_mgmt_service(setup_info)
    cm.hosts_start_roles([hostname])


@cloudera_cmd
def format_namenode(hdfs_service):
    for nn in hdfs_service.get_roles_by_type('NAMENODE'):
        yield hdfs_service.format_hdfs(nn.name)[0]


@cloudera_cmd
def start_service(service):
    yield service.start()


@cloudera_cmd
def start_roles(service, *role_names):
    for role in service.start_roles(*role_names):
        yield role


@cloudera_cmd
def create_yarn_job_history_dir(yarn_service):
    yield yarn_service.create_yarn_job_history_dir()


@cloudera_cmd
def create_oozie_db(oozie_service):
    yield oozie_service.create_oozie_db()


@cloudera_cmd
def install_oozie_sharelib(oozie_service):
    yield oozie_service.install_oozie_sharelib()


@cloudera_cmd
def create_hive_metastore_db(hive_service):
    yield hive_service.create_hive_metastore_tables()


@cloudera_cmd
def create_hive_dirs(hive_service):
    yield hive_service.create_hive_userdir()
    yield hive_service.create_hive_warehouse()
