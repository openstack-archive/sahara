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

import six

from sahara import context
from sahara.i18n import _
from sahara.plugins.cdh.client import api_client
from sahara.plugins.cdh.client import services
from sahara.plugins.cdh import db_helper as dh
from sahara.plugins.cdh import plugin_utils
from sahara.plugins.cdh import validation
from sahara.plugins import exceptions as ex
from sahara.plugins import kerberos
from sahara.swift import swift_helper
from sahara.topology import topology_helper as t_helper
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import configs as s_cfg
from sahara.utils import poll_utils
from sahara.utils import xmlutils


HDFS_SERVICE_TYPE = 'HDFS'
YARN_SERVICE_TYPE = 'YARN'
OOZIE_SERVICE_TYPE = 'OOZIE'
HIVE_SERVICE_TYPE = 'HIVE'
HUE_SERVICE_TYPE = 'HUE'
SPARK_SERVICE_TYPE = 'SPARK_ON_YARN'
ZOOKEEPER_SERVICE_TYPE = 'ZOOKEEPER'
HBASE_SERVICE_TYPE = 'HBASE'
FLUME_SERVICE_TYPE = 'FLUME'
SENTRY_SERVICE_TYPE = 'SENTRY'
SOLR_SERVICE_TYPE = 'SOLR'
SQOOP_SERVICE_TYPE = 'SQOOP'
KS_INDEXER_SERVICE_TYPE = 'KS_INDEXER'
IMPALA_SERVICE_TYPE = 'IMPALA'
KMS_SERVICE_TYPE = 'KMS'
KAFKA_SERVICE_TYPE = 'KAFKA'


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


class ClouderaUtils(object):
    CM_DEFAULT_USERNAME = 'admin'
    CM_DEFAULT_PASSWD = 'admin'
    CM_API_VERSION = 8

    HDFS_SERVICE_NAME = 'hdfs01'
    YARN_SERVICE_NAME = 'yarn01'
    OOZIE_SERVICE_NAME = 'oozie01'
    HIVE_SERVICE_NAME = 'hive01'
    HUE_SERVICE_NAME = 'hue01'
    SPARK_SERVICE_NAME = 'spark_on_yarn01'
    ZOOKEEPER_SERVICE_NAME = 'zookeeper01'
    HBASE_SERVICE_NAME = 'hbase01'

    FLUME_SERVICE_NAME = 'flume01'
    SOLR_SERVICE_NAME = 'solr01'
    SQOOP_SERVICE_NAME = 'sqoop01'
    KS_INDEXER_SERVICE_NAME = 'ks_indexer01'
    IMPALA_SERVICE_NAME = 'impala01'
    SENTRY_SERVICE_NAME = 'sentry01'
    KMS_SERVICE_NAME = 'kms01'
    KAFKA_SERVICE_NAME = 'kafka01'
    NAME_SERVICE = 'nameservice01'

    def __init__(self):
        self.pu = plugin_utils.AbstractPluginUtils()
        self.validator = validation.Validator
        self.c_helper = None

    def get_api_client_by_default_password(self, cluster):
        manager_ip = self.pu.get_manager(cluster).management_ip
        return api_client.ApiResource(manager_ip,
                                      username=self.CM_DEFAULT_USERNAME,
                                      password=self.CM_DEFAULT_PASSWD,
                                      version=self.CM_API_VERSION)

    def get_api_client(self, cluster, api_version=None):
        manager_ip = self.pu.get_manager(cluster).management_ip
        cm_password = dh.get_cm_password(cluster)
        version = self.CM_API_VERSION if not api_version else api_version
        return api_client.ApiResource(manager_ip,
                                      username=self.CM_DEFAULT_USERNAME,
                                      password=cm_password,
                                      version=version)

    def update_cloudera_password(self, cluster):
        api = self.get_api_client_by_default_password(cluster)
        user = api.get_user(self.CM_DEFAULT_USERNAME)
        user.password = dh.get_cm_password(cluster)
        api.update_user(user)

    def get_cloudera_cluster(self, cluster):
        api = self.get_api_client(cluster)
        return api.get_cluster(cluster.name)

    @cloudera_cmd
    def start_cloudera_cluster(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)
        yield cm_cluster.start()

    @cloudera_cmd
    def stop_cloudera_cluster(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)
        yield cm_cluster.stop()

    def start_instances(self, cluster):
        self.start_cloudera_cluster(cluster)

    @cpo.event_wrapper(True, step=_("Delete instances"), param=('cluster', 1))
    def delete_instances(self, cluster, instances):
        api = self.get_api_client(cluster)
        cm_cluster = self.get_cloudera_cluster(cluster)
        hosts = api.get_all_hosts(view='full')
        hostsnames_to_deleted = [i.fqdn() for i in instances]
        for host in hosts:
            if host.hostname in hostsnames_to_deleted:
                cm_cluster.remove_host(host.hostId)
                api.delete_host(host.hostId)

    @cpo.event_wrapper(
        True, step=_("Decommission nodes"), param=('cluster', 1))
    def decommission_nodes(self, cluster, process,
                           decommission_roles, roles_to_delete=None):
        service = self.get_service_by_role(process, cluster)
        service.decommission(*decommission_roles).wait()
        # not all roles should be decommissioned
        if roles_to_delete:
            decommission_roles.extend(roles_to_delete)
        for role_name in decommission_roles:
            service.delete_role(role_name)

    @cpo.event_wrapper(
        True, step=_("Refresh DataNodes"), param=('cluster', 1))
    def refresh_datanodes(self, cluster):
        self._refresh_nodes(cluster, 'DATANODE', self.HDFS_SERVICE_NAME)

    @cpo.event_wrapper(
        True, step=_("Refresh YARNNodes"), param=('cluster', 1))
    def refresh_yarn_nodes(self, cluster):
        self._refresh_nodes(cluster, 'NODEMANAGER', self.YARN_SERVICE_NAME)

    @cloudera_cmd
    def _refresh_nodes(self, cluster, process, service_name):
        cm_cluster = self.get_cloudera_cluster(cluster)
        service = cm_cluster.get_service(service_name)
        nds = [n.name for n in service.get_roles_by_type(process)]
        for nd in nds:
            for st in service.refresh(nd):
                yield st

    @cpo.event_wrapper(
        True, step=_("Restart stale services"), param=('cluster', 1))
    @cloudera_cmd
    def restart_stale_services(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)
        yield cm_cluster.restart(
            restart_only_stale_services=True,
            redeploy_client_configuration=True)

    @cpo.event_wrapper(True, step=_("Deploy configs"), param=('cluster', 1))
    @cloudera_cmd
    def deploy_configs(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)
        yield cm_cluster.deploy_client_config()

    def update_configs(self, instances):
        # instances non-empty
        cpo.add_provisioning_step(
            instances[0].cluster_id, _("Update configs"), len(instances))
        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn("update-configs-%s" % instance.instance_name,
                         self._update_configs, instance)
                context.sleep(1)

    @cpo.event_wrapper(True)
    @cloudera_cmd
    def _update_configs(self, instance):
        for process in instance.node_group.node_processes:
            process = self.pu.convert_role_showname(process)
            service = self.get_service_by_role(process, instance=instance)
            yield service.deploy_client_config(self.pu.get_role_name(instance,
                                                                     process))

    def get_mgmt_service(self, cluster):
        api = self.get_api_client(cluster)
        cm = api.get_cloudera_manager()
        mgmt_service = cm.get_service()
        return mgmt_service

    @cloudera_cmd
    def restart_mgmt_service(self, cluster):
        service = self.get_mgmt_service(cluster)
        yield service.restart()

    @cloudera_cmd
    def start_service(self, service):
        yield service.start()

    @cloudera_cmd
    def stop_service(self, service):
        yield service.stop()

    @cloudera_cmd
    def start_roles(self, service, *role_names):
        for role in service.start_roles(*role_names):
            yield role

    @cpo.event_wrapper(
        True, step=_("Create mgmt service"), param=('cluster', 1))
    def create_mgmt_service(self, cluster):
        api = self.get_api_client(cluster)
        cm = api.get_cloudera_manager()

        setup_info = services.ApiServiceSetupInfo()
        manager = self.pu.get_manager(cluster)
        hostname = manager.fqdn()
        processes = ['SERVICEMONITOR', 'HOSTMONITOR',
                     'EVENTSERVER', 'ALERTPUBLISHER']
        for proc in processes:
            setup_info.add_role_info(self.pu.get_role_name(manager, proc),
                                     proc, hostname)

        cm.create_mgmt_service(setup_info)
        cm.hosts_start_roles([hostname])

    def get_service_by_role(self, role, cluster=None, instance=None):
        if cluster:
            cm_cluster = self.get_cloudera_cluster(cluster)
        elif instance:
            cm_cluster = self.get_cloudera_cluster(instance.cluster)
        else:
            raise ValueError(_("'cluster' or 'instance' argument missed"))

        if role in ['NAMENODE', 'DATANODE', 'SECONDARYNAMENODE',
                    'HDFS_GATEWAY']:
            return cm_cluster.get_service(self.HDFS_SERVICE_NAME)
        elif role in ['RESOURCEMANAGER', 'NODEMANAGER', 'JOBHISTORY',
                      'YARN_GATEWAY']:
            return cm_cluster.get_service(self.YARN_SERVICE_NAME)
        elif role in ['OOZIE_SERVER']:
            return cm_cluster.get_service(self.OOZIE_SERVICE_NAME)
        elif role in ['HIVESERVER2', 'HIVEMETASTORE', 'WEBHCAT']:
            return cm_cluster.get_service(self.HIVE_SERVICE_NAME)
        elif role in ['HUE_SERVER']:
            return cm_cluster.get_service(self.HUE_SERVICE_NAME)
        elif role in ['SPARK_YARN_HISTORY_SERVER']:
            return cm_cluster.get_service(self.SPARK_SERVICE_NAME)
        elif role in ['SERVER']:
            return cm_cluster.get_service(self.ZOOKEEPER_SERVICE_NAME)
        elif role in ['MASTER', 'REGIONSERVER']:
            return cm_cluster.get_service(self.HBASE_SERVICE_NAME)
        elif role in ['AGENT']:
            return cm_cluster.get_service(self.FLUME_SERVICE_NAME)
        elif role in ['SENTRY_SERVER']:
            return cm_cluster.get_service(self.SENTRY_SERVICE_NAME)
        elif role in ['SQOOP_SERVER']:
            return cm_cluster.get_service(self.SQOOP_SERVICE_NAME)
        elif role in ['SOLR_SERVER']:
            return cm_cluster.get_service(self.SOLR_SERVICE_NAME)
        elif role in ['HBASE_INDEXER']:
            return cm_cluster.get_service(self.KS_INDEXER_SERVICE_NAME)
        elif role in ['CATALOGSERVER', 'STATESTORE', 'IMPALAD', 'LLAMA']:
            return cm_cluster.get_service(self.IMPALA_SERVICE_NAME)
        elif role in ['KMS']:
            return cm_cluster.get_service(self.KMS_SERVICE_NAME)
        elif role in ['JOURNALNODE']:
            return cm_cluster.get_service(self.HDFS_SERVICE_NAME)
        elif role in ['YARN_STANDBYRM']:
            return cm_cluster.get_service(self.YARN_SERVICE_NAME)
        elif role in ['KAFKA_BROKER']:
            return cm_cluster.get_service(self.KAFKA_SERVICE_NAME)
        else:
            raise ValueError(
                _("Process %(process)s is not supported by CDH plugin") %
                {'process': role})

    @cpo.event_wrapper(
        True, step=_("First run cluster"), param=('cluster', 1))
    @cloudera_cmd
    def first_run(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)
        yield cm_cluster.first_run()

    @cpo.event_wrapper(True, step=_("Create services"), param=('cluster', 1))
    def create_services(self, cluster):
        api = self.get_api_client(cluster)
        cm_cluster = api.create_cluster(cluster.name,
                                        fullVersion=cluster.hadoop_version)

        if len(self.pu.get_zookeepers(cluster)) > 0:
            cm_cluster.create_service(self.ZOOKEEPER_SERVICE_NAME,
                                      ZOOKEEPER_SERVICE_TYPE)
        cm_cluster.create_service(self.HDFS_SERVICE_NAME, HDFS_SERVICE_TYPE)
        cm_cluster.create_service(self.YARN_SERVICE_NAME, YARN_SERVICE_TYPE)
        cm_cluster.create_service(self.OOZIE_SERVICE_NAME, OOZIE_SERVICE_TYPE)
        if self.pu.get_hive_metastore(cluster):
            cm_cluster.create_service(self.HIVE_SERVICE_NAME,
                                      HIVE_SERVICE_TYPE)
        if self.pu.get_hue(cluster):
            cm_cluster.create_service(self.HUE_SERVICE_NAME, HUE_SERVICE_TYPE)
        if self.pu.get_spark_historyserver(cluster):
            cm_cluster.create_service(self.SPARK_SERVICE_NAME,
                                      SPARK_SERVICE_TYPE)
        if self.pu.get_hbase_master(cluster):
            cm_cluster.create_service(self.HBASE_SERVICE_NAME,
                                      HBASE_SERVICE_TYPE)
        if len(self.pu.get_flumes(cluster)) > 0:
            cm_cluster.create_service(self.FLUME_SERVICE_NAME,
                                      FLUME_SERVICE_TYPE)
        if self.pu.get_sentry(cluster):
            cm_cluster.create_service(self.SENTRY_SERVICE_NAME,
                                      SENTRY_SERVICE_TYPE)
        if len(self.pu.get_solrs(cluster)) > 0:
            cm_cluster.create_service(self.SOLR_SERVICE_NAME,
                                      SOLR_SERVICE_TYPE)
        if self.pu.get_sqoop(cluster):
            cm_cluster.create_service(self.SQOOP_SERVICE_NAME,
                                      SQOOP_SERVICE_TYPE)
        if len(self.pu.get_hbase_indexers(cluster)) > 0:
            cm_cluster.create_service(self.KS_INDEXER_SERVICE_NAME,
                                      KS_INDEXER_SERVICE_TYPE)
        if self.pu.get_catalogserver(cluster):
            cm_cluster.create_service(self.IMPALA_SERVICE_NAME,
                                      IMPALA_SERVICE_TYPE)
        if self.pu.get_kms(cluster):
            cm_cluster.create_service(self.KMS_SERVICE_NAME,
                                      KMS_SERVICE_TYPE)
        if len(self.pu.get_kafka_brokers(cluster)) > 0:
            cm_cluster.create_service(self.KAFKA_SERVICE_NAME,
                                      KAFKA_SERVICE_TYPE)

    def _agents_connected(self, instances, api):
        hostnames = [i.fqdn() for i in instances]
        hostnames_to_manager = [h.hostname for h in
                                api.get_all_hosts('full')]
        for hostname in hostnames:
            if hostname not in hostnames_to_manager:
                return False
        return True

    @cpo.event_wrapper(True, step=_("Await agents"), param=('cluster', 1))
    def _await_agents(self, cluster, instances, timeout_config):
        api = self.get_api_client(instances[0].cluster)
        poll_utils.plugin_option_poll(
            cluster, self._agents_connected, timeout_config,
            _("Await Cloudera agents"), 5, {
                'instances': instances, 'api': api})

    def await_agents(self, cluster, instances):
        self._await_agents(cluster, instances,
                           self.c_helper.AWAIT_AGENTS_TIMEOUT)

    @cpo.event_wrapper(
        True, step=_("Configure services"), param=('cluster', 1))
    def configure_services(self, cluster):
        cm_cluster = self.get_cloudera_cluster(cluster)

        if len(self.pu.get_zookeepers(cluster)) > 0:
            zookeeper = cm_cluster.get_service(self.ZOOKEEPER_SERVICE_NAME)
            zookeeper.update_config(self._get_configs(ZOOKEEPER_SERVICE_TYPE,
                                                      cluster=cluster))

        hdfs = cm_cluster.get_service(self.HDFS_SERVICE_NAME)
        hdfs.update_config(self._get_configs(HDFS_SERVICE_TYPE,
                                             cluster=cluster))

        yarn = cm_cluster.get_service(self.YARN_SERVICE_NAME)
        yarn.update_config(self._get_configs(YARN_SERVICE_TYPE,
                                             cluster=cluster))

        oozie = cm_cluster.get_service(self.OOZIE_SERVICE_NAME)
        oozie.update_config(self._get_configs(OOZIE_SERVICE_TYPE,
                                              cluster=cluster))

        if self.pu.get_hive_metastore(cluster):
            hive = cm_cluster.get_service(self.HIVE_SERVICE_NAME)
            hive.update_config(self._get_configs(HIVE_SERVICE_TYPE,
                                                 cluster=cluster))

        if self.pu.get_hue(cluster):
            hue = cm_cluster.get_service(self.HUE_SERVICE_NAME)
            hue.update_config(self._get_configs(HUE_SERVICE_TYPE,
                                                cluster=cluster))

        if self.pu.get_spark_historyserver(cluster):
            spark = cm_cluster.get_service(self.SPARK_SERVICE_NAME)
            spark.update_config(self._get_configs(SPARK_SERVICE_TYPE,
                                                  cluster=cluster))

        if self.pu.get_hbase_master(cluster):
            hbase = cm_cluster.get_service(self.HBASE_SERVICE_NAME)
            hbase.update_config(self._get_configs(HBASE_SERVICE_TYPE,
                                                  cluster=cluster))

        if len(self.pu.get_flumes(cluster)) > 0:
            flume = cm_cluster.get_service(self.FLUME_SERVICE_NAME)
            flume.update_config(self._get_configs(FLUME_SERVICE_TYPE,
                                                  cluster=cluster))

        if self.pu.get_sentry(cluster):
            sentry = cm_cluster.get_service(self.SENTRY_SERVICE_NAME)
            sentry.update_config(self._get_configs(SENTRY_SERVICE_TYPE,
                                                   cluster=cluster))

        if len(self.pu.get_solrs(cluster)) > 0:
            solr = cm_cluster.get_service(self.SOLR_SERVICE_NAME)
            solr.update_config(self._get_configs(SOLR_SERVICE_TYPE,
                                                 cluster=cluster))

        if self.pu.get_sqoop(cluster):
            sqoop = cm_cluster.get_service(self.SQOOP_SERVICE_NAME)
            sqoop.update_config(self._get_configs(SQOOP_SERVICE_TYPE,
                                                  cluster=cluster))

        if len(self.pu.get_hbase_indexers(cluster)) > 0:
            ks_indexer = cm_cluster.get_service(self.KS_INDEXER_SERVICE_NAME)
            ks_indexer.update_config(
                self._get_configs(KS_INDEXER_SERVICE_TYPE, cluster=cluster))

        if self.pu.get_catalogserver(cluster):
            impala = cm_cluster.get_service(self.IMPALA_SERVICE_NAME)
            impala.update_config(self._get_configs(IMPALA_SERVICE_TYPE,
                                                   cluster=cluster))

        if self.pu.get_kms(cluster):
            kms = cm_cluster.get_service(self.KMS_SERVICE_NAME)
            kms.update_config(self._get_configs(KMS_SERVICE_TYPE,
                                                cluster=cluster))
        if len(self.pu.get_kafka_brokers(cluster)) > 0:
            kafka = cm_cluster.get_service(self.KAFKA_SERVICE_NAME)
            kafka.update_config(self._get_configs(KAFKA_SERVICE_TYPE,
                                                  cluster=cluster))

    def configure_instances(self, instances, cluster=None):
        # instances non-empty
        cpo.add_provisioning_step(
            instances[0].cluster_id, _("Configure instances"), len(instances))
        for inst in instances:
            self.configure_instance(inst, cluster)

    def get_roles_list(self, node_processes):
        current = set(node_processes)
        extra_roles = {
            'YARN_GATEWAY': ["YARN_NODEMANAGER"],
            'HDFS_GATEWAY': ['HDFS_NAMENODE', 'HDFS_DATANODE',
                             "HDFS_SECONDARYNAMENODE"]
        }
        for extra_role in six.iterkeys(extra_roles):
            valid_processes = extra_roles[extra_role]
            for valid in valid_processes:
                if valid in current:
                    current.add(extra_role)
                    break
        return list(current)

    def get_role_type(self, process):
        mapper = {
            'YARN_GATEWAY': 'GATEWAY',
            'HDFS_GATEWAY': 'GATEWAY',
        }
        return mapper.get(process, process)

    @cpo.event_wrapper(True)
    def configure_instance(self, instance, cluster=None):
        roles_list = self.get_roles_list(instance.node_group.node_processes)
        for role in roles_list:
            self._add_role(instance, role, cluster)

    def _add_role(self, instance, process, cluster):
        if process in ['CLOUDERA_MANAGER', 'HDFS_JOURNALNODE',
                       'YARN_STANDBYRM']:
            return

        process = self.pu.convert_role_showname(process)
        service = self.get_service_by_role(process, instance=instance)
        role_type = self.get_role_type(process)
        role = service.create_role(self.pu.get_role_name(instance, process),
                                   role_type, instance.fqdn())
        role.update_config(self._get_configs(process, cluster,
                                             instance=instance))

    @cloudera_cmd
    def restart_service(self, process, instance):
        service = self.get_service_by_role(process, instance=instance)
        yield service.restart()

    def update_role_config(self, instance, process):
        process = self.pu.convert_role_showname(process)
        service = self.get_service_by_role(process, instance=instance)
        api = self.get_api_client(instance.cluster)
        hosts = api.get_all_hosts(view='full')
        ihost_id = None
        for host in hosts:
            if instance.fqdn() == host.hostname:
                ihost_id = host.hostId
                break
        role_type = self.get_role_type(process)
        roles = service.get_roles_by_type(role_type)
        for role in roles:
            if role.hostRef.hostId == ihost_id:
                role.update_config(
                    self._get_configs(role_type, instance=instance))
        self.restart_service(process, instance)

    @cloudera_cmd
    def import_admin_credentials(self, cm, username, password):
        yield cm.import_admin_credentials(username, password)

    @cloudera_cmd
    def configure_for_kerberos(self, cluster):
        api = self.get_api_client(cluster, api_version=11)
        cluster = api.get_cluster(cluster.name)
        yield cluster.configure_for_kerberos()

    def push_kerberos_configs(self, cluster):
        manager = self.pu.get_manager(cluster)
        kdc_host = kerberos.get_kdc_host(cluster, manager)
        security_realm = kerberos.get_realm_name(cluster)
        username = "%s@%s" % (kerberos.get_admin_principal(cluster),
                              kerberos.get_realm_name(cluster))
        password = kerberos.get_server_password(cluster)

        api = self.get_api_client(cluster)
        cm = api.get_cloudera_manager()
        cm.update_config({'SECURITY_REALM': security_realm,
                          'KDC_HOST': kdc_host})

        self.import_admin_credentials(cm, username, password)
        self.configure_for_kerberos(cluster)
        self.deploy_configs(cluster)

    def configure_rack_awareness(self, cluster):
        if t_helper.is_data_locality_enabled():
            self._configure_rack_awareness(cluster)

    @cpo.event_wrapper(
        True, step=_("Configure rack awareness"), param=('cluster', 1))
    def _configure_rack_awareness(self, cluster):
        api = self.get_api_client(cluster)
        topology = t_helper.generate_topology_map(
            cluster, is_node_awareness=False)
        for host in api.get_all_hosts():
            host.rackId = topology[host.ipAddress]
            host.put_host()

    def full_cluster_stop(self, cluster):
        self.stop_cloudera_cluster(cluster)
        mgmt = self.get_mgmt_service(cluster)
        self.stop_service(mgmt)

    def full_cluster_start(self, cluster):
        self.start_cloudera_cluster(cluster)
        mgmt = self.get_mgmt_service(cluster)
        self.start_service(mgmt)

    def get_cloudera_manager_info(self, cluster):
        mng = self.pu.get_manager(cluster)
        info = {
            'Cloudera Manager': {
                'Web UI': 'http://%s:7180' % mng.get_ip_or_dns_name(),
                'Username': 'admin',
                'Password': dh.get_cm_password(cluster)
            }
        }
        return info

    @cpo.event_wrapper(
        True, step=_("Enable NameNode HA"), param=('cluster', 1))
    @cloudera_cmd
    def enable_namenode_ha(self, cluster):
        standby_nn = self.pu.get_secondarynamenode(cluster)
        standby_nn_host_name = standby_nn.fqdn()
        jns = self.pu.get_jns(cluster)
        jn_list = []
        for index, jn in enumerate(jns):
            jn_host_name = jn.fqdn()
            jn_list.append({'jnHostId': jn_host_name,
                            'jnName': 'JN%i' % index,
                            'jnEditsDir': '/dfs/jn'
                            })
        cm_cluster = self.get_cloudera_cluster(cluster)
        hdfs = cm_cluster.get_service(self.HDFS_SERVICE_NAME)
        nn = hdfs.get_roles_by_type('NAMENODE')[0]

        yield hdfs.enable_nn_ha(active_name=nn.name,
                                standby_host_id=standby_nn_host_name,
                                nameservice=self.NAME_SERVICE, jns=jn_list
                                )

    @cpo.event_wrapper(
        True, step=_("Enable ResourceManager HA"), param=('cluster', 1))
    @cloudera_cmd
    def enable_resourcemanager_ha(self, cluster):
        new_rm = self.pu.get_stdb_rm(cluster)
        new_rm_host_name = new_rm.fqdn()
        cm_cluster = self.get_cloudera_cluster(cluster)
        yarn = cm_cluster.get_service(self.YARN_SERVICE_NAME)
        yield yarn.enable_rm_ha(new_rm_host_id=new_rm_host_name)

    def _load_version_specific_instance_configs(self, instance, default_conf):
        pass

    def _get_configs(self, service, cluster=None, instance=None):
        def get_hadoop_dirs(mount_points, suffix):
            return ','.join([x + suffix for x in mount_points])

        all_confs = {}
        if cluster:
            zk_count = self.validator.get_inst_count(cluster,
                                                     'ZOOKEEPER_SERVER')
            hbm_count = self.validator.get_inst_count(cluster, 'HBASE_MASTER')
            snt_count = self.validator.get_inst_count(cluster,
                                                      'SENTRY_SERVER')
            ks_count =\
                self.validator.get_inst_count(cluster,
                                              'KEY_VALUE_STORE_INDEXER')
            kms_count = self.validator.get_inst_count(cluster, 'KMS')
            imp_count =\
                self.validator.get_inst_count(cluster,
                                              'IMPALA_CATALOGSERVER')
            hive_count = self.validator.get_inst_count(cluster,
                                                       'HIVE_METASTORE')
            slr_count = self.validator.get_inst_count(cluster, 'SOLR_SERVER')
            sqp_count = self.validator.get_inst_count(cluster, 'SQOOP_SERVER')
            core_site_safety_valve = ''
            if self.pu.c_helper.is_swift_enabled(cluster):
                configs = swift_helper.get_swift_configs()
                confs = {c['name']: c['value'] for c in configs}
                core_site_safety_valve = xmlutils.create_elements_xml(confs)
            all_confs = {
                'HDFS': {
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else '',
                    'dfs_block_local_path_access_user':
                        'impala' if imp_count else '',
                    'kms_service': self.KMS_SERVICE_NAME if kms_count else '',
                    'core_site_safety_valve': core_site_safety_valve
                },
                'HIVE': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME,
                    'sentry_service':
                        self.SENTRY_SERVICE_NAME if snt_count else '',
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'OOZIE': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME,
                    'hive_service':
                        self.HIVE_SERVICE_NAME if hive_count else '',
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'YARN': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                },
                'HUE': {
                    'hive_service': self.HIVE_SERVICE_NAME,
                    'oozie_service': self.OOZIE_SERVICE_NAME,
                    'sentry_service':
                        self.SENTRY_SERVICE_NAME if snt_count else '',
                    'solr_service':
                        self.SOLR_SERVICE_NAME if slr_count else '',
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else '',
                    'hbase_service':
                        self.HBASE_SERVICE_NAME if hbm_count else '',
                    'impala_service':
                        self.IMPALA_SERVICE_NAME if imp_count else '',
                    'sqoop_service':
                        self.SQOOP_SERVICE_NAME if sqp_count else ''
                },
                'SPARK_ON_YARN': {
                    'yarn_service': self.YARN_SERVICE_NAME
                },
                'HBASE': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'zookeeper_service': self.ZOOKEEPER_SERVICE_NAME,
                    'hbase_enable_indexing': 'true' if ks_count else 'false',
                    'hbase_enable_replication':
                        'true' if ks_count else 'false'
                },
                'FLUME': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'solr_service':
                        self.SOLR_SERVICE_NAME if slr_count else '',
                    'hbase_service':
                        self.HBASE_SERVICE_NAME if hbm_count else ''
                },
                'SENTRY': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'sentry_server_config_safety_valve': (
                        self.c_helper.SENTRY_IMPALA_CLIENT_SAFETY_VALVE
                        if imp_count else '')
                },
                'SOLR': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'zookeeper_service': self.ZOOKEEPER_SERVICE_NAME
                },
                'SQOOP': {
                    'mapreduce_yarn_service': self.YARN_SERVICE_NAME
                },
                'KS_INDEXER': {
                    'hbase_service': self.HBASE_SERVICE_NAME,
                    'solr_service': self.SOLR_SERVICE_NAME
                },
                'IMPALA': {
                    'hdfs_service': self.HDFS_SERVICE_NAME,
                    'hbase_service':
                        self.HBASE_SERVICE_NAME if hbm_count else '',
                    'hive_service': self.HIVE_SERVICE_NAME,
                    'sentry_service':
                        self.SENTRY_SERVICE_NAME if snt_count else '',
                    'zookeeper_service':
                        self.ZOOKEEPER_SERVICE_NAME if zk_count else ''
                }
            }
            hive_confs = {
                'HIVE': {
                    'hive_metastore_database_type': 'postgresql',
                    'hive_metastore_database_host':
                        self.pu.get_manager(cluster).internal_ip,
                    'hive_metastore_database_port': '7432',
                    'hive_metastore_database_password':
                        dh.get_hive_db_password(cluster)
                }
            }
            hue_confs = {
                'HUE': {
                    'hue_webhdfs': self.pu.get_role_name(
                        self.pu.get_namenode(cluster), 'NAMENODE')
                }
            }
            sentry_confs = {
                'SENTRY': {
                    'sentry_server_database_type': 'postgresql',
                    'sentry_server_database_host':
                        self.pu.get_manager(cluster).internal_ip,
                    'sentry_server_database_port': '7432',
                    'sentry_server_database_password':
                        dh.get_sentry_db_password(cluster)
                }
            }
            kafka_confs = {
                'KAFKA': {
                    'zookeeper_service': self.ZOOKEEPER_SERVICE_NAME
                }
            }
            all_confs = s_cfg.merge_configs(all_confs, hue_confs)
            all_confs = s_cfg.merge_configs(all_confs, hive_confs)
            all_confs = s_cfg.merge_configs(all_confs, sentry_confs)
            all_confs = s_cfg.merge_configs(all_confs, kafka_confs)
            all_confs = s_cfg.merge_configs(all_confs, cluster.cluster_configs)

        if instance:
            snt_count = self.validator.get_inst_count(instance.cluster,
                                                      'SENTRY_SERVER')
            paths = instance.storage_paths()

            instance_default_confs = {
                'NAMENODE': {
                    'dfs_name_dir_list': get_hadoop_dirs(paths, '/fs/nn')
                },
                'SECONDARYNAMENODE': {
                    'fs_checkpoint_dir_list':
                        get_hadoop_dirs(paths, '/fs/snn')
                },
                'DATANODE': {
                    'dfs_data_dir_list': get_hadoop_dirs(paths, '/fs/dn'),
                    'dfs_datanode_data_dir_perm': 755,
                    'dfs_datanode_handler_count': 30
                },
                'NODEMANAGER': {
                    'yarn_nodemanager_local_dirs':
                        get_hadoop_dirs(paths, '/yarn/local'),
                    'container_executor_allowed_system_users':
                        "nobody,impala,hive,llama,hdfs,yarn,mapred,"
                        "spark,oozie",
                    "container_executor_banned_users": "bin"
                },
                'SERVER': {
                    'maxSessionTimeout': 60000
                },
                'HIVESERVER2': {
                    'hiveserver2_enable_impersonation':
                        'false' if snt_count else 'true',
                    'hive_hs2_config_safety_valve': (
                        self.c_helper.HIVE_SERVER2_SENTRY_SAFETY_VALVE
                        if snt_count else '')
                },
                'HIVEMETASTORE': {
                    'hive_metastore_config_safety_valve': (
                        self.c_helper.HIVE_METASTORE_SENTRY_SAFETY_VALVE
                        if snt_count else '')
                }
            }

            self._load_version_specific_instance_configs(
                instance, instance_default_confs)

            ng_user_confs = self.pu.convert_process_configs(
                instance.node_group.node_configs)
            all_confs = s_cfg.merge_configs(all_confs, ng_user_confs)
            all_confs = s_cfg.merge_configs(all_confs, instance_default_confs)

        return all_confs.get(service, {})
