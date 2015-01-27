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
ZOOKEEPER_SERVICE_NAME = 'zookeeper01'
HBASE_SERVICE_NAME = 'hbase01'
FLUME_SERVICE_NAME = 'flume01'
SENTRY_SERVICE_NAME = 'sentry01'
SOLR_SERVICE_NAME = 'solr01'
SQOOP_SERVICE_NAME = 'sqoop01'
KS_INDEXER_SERVICE_NAME = 'ks_indexer01'
IMPALA_SERVICE_NAME = 'impala01'


def have_cm_api_libs():
    return api_client and services


def cloudera_cmd(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        for cmd in f(*args, **kwargs):
            result = cmd.wait()
            if not result.success:
                if result.children is not None:
                    for c in result.children:
                        if not c.success:
                            raise ex.HadoopProvisionError(c.resultMessage)
                else:
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
    elif process in ['SERVER']:
        return cm_cluster.get_service(ZOOKEEPER_SERVICE_NAME)
    elif process in ['MASTER', 'REGIONSERVER']:
        return cm_cluster.get_service(HBASE_SERVICE_NAME)
    elif process in ['AGENT']:
        return cm_cluster.get_service(FLUME_SERVICE_NAME)
    elif process in ['SQOOP_SERVER']:
        return cm_cluster.get_service(SQOOP_SERVICE_NAME)
    elif process in ['SENTRY_SERVER']:
        return cm_cluster.get_service(SENTRY_SERVICE_NAME)
    elif process in ['SOLR_SERVER']:
        return cm_cluster.get_service(SOLR_SERVICE_NAME)
    elif process in ['HBASE_INDEXER']:
        return cm_cluster.get_service(KS_INDEXER_SERVICE_NAME)
    elif process in ['CATALOGSERVER', 'STATESTORE', 'IMPALAD', 'LLAMA']:
        return cm_cluster.get_service(IMPALA_SERVICE_NAME)
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


@cloudera_cmd
def first_run(cluster):
    cm_cluster = get_cloudera_cluster(cluster)
    yield cm_cluster.first_run()


def get_role_name(instance, service):
    # NOTE: role name must match regexp "[_A-Za-z][-_A-Za-z0-9]{0,63}"
    shortcuts = {
        'AGENT': 'A',
        'ALERTPUBLISHER': 'AP',
        'CATALOGSERVER': 'ICS',
        'DATANODE': 'DN',
        'EVENTSERVER': 'ES',
        'HBASE_INDEXER': 'LHBI',
        'HIVEMETASTORE': 'HVM',
        'HIVESERVER2': 'HVS',
        'HOSTMONITOR': 'HM',
        'IMPALAD': 'ID',
        'JOBHISTORY': 'JS',
        'MASTER': 'M',
        'NAMENODE': 'NN',
        'NODEMANAGER': 'NM',
        'OOZIE_SERVER': 'OS',
        'REGIONSERVER': 'RS',
        'RESOURCEMANAGER': 'RM',
        'SECONDARYNAMENODE': 'SNN',
        'SENTRY_SERVER': 'SNT',
        'SERVER': 'S',
        'SERVICEMONITOR': 'SM',
        'SOLR_SERVER': 'SLR',
        'SPARK_YARN_HISTORY_SERVER': 'SHS',
        'SQOOP_SERVER': 'S2S',
        'STATESTORE': 'ISS',
        'WEBHCAT': 'WHC'
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
def restart_mgmt_service(cluster):
    api = get_api_client(cluster)
    cm = api.get_cloudera_manager()
    mgmt_service = cm.get_service()
    yield mgmt_service.restart()


@cloudera_cmd
def start_service(service):
    yield service.start()


@cloudera_cmd
def start_roles(service, *role_names):
    for role in service.start_roles(*role_names):
        yield role
