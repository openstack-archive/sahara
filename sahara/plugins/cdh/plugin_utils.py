# Copyright (c) 2014 Intel Corporation.
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
# This file only contains utils not related to cm_api, while in
# cloudera_utils the functios are cm_api involved.

import os
import telnetlib

from oslo_log import log as logging
from oslo_utils import timeutils

from sahara.conductor import resource as res
from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.plugins.cdh import commands as cmd
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import edp as edp_u


PATH_TO_CORE_SITE_XML = '/etc/hadoop/conf/core-site.xml'
HADOOP_LIB_DIR = '/usr/lib/hadoop-mapreduce'

CM_API_PORT = 7180

LOG = logging.getLogger(__name__)


class AbstractPluginUtils(object):
    # c_helper and db_helper will be defined in derived classes.
    c_helper = None
    db_helper = None

    def get_role_name(self, instance, service):
        # NOTE: role name must match regexp "[_A-Za-z][-_A-Za-z0-9]{0,63}"
        shortcuts = {
            'ALERTPUBLISHER': 'AP',
            'DATANODE': 'DN',
            'EVENTSERVER': 'ES',
            'HIVEMETASTORE': 'HVM',
            'HIVESERVER2': 'HVS',
            'HOSTMONITOR': 'HM',
            'JOBHISTORY': 'JS',
            'MASTER': 'M',
            'NAMENODE': 'NN',
            'NODEMANAGER': 'NM',
            'OOZIE_SERVER': 'OS',
            'REGIONSERVER': 'RS',
            'RESOURCEMANAGER': 'RM',
            'SECONDARYNAMENODE': 'SNN',
            'SERVER': 'S',
            'SERVICEMONITOR': 'SM',
            'SPARK_YARN_HISTORY_SERVER': 'SHS',
            'WEBHCAT': 'WHC'
        }
        return '%s_%s' % (shortcuts.get(service, service),
                          instance.hostname().replace('-', '_'))

    def get_manager(self, cluster):
        return u.get_instance(cluster, 'CLOUDERA_MANAGER')

    def get_namenode(self, cluster):
        return u.get_instance(cluster, "HDFS_NAMENODE")

    def get_datanodes(self, cluster):
        return u.get_instances(cluster, 'HDFS_DATANODE')

    def get_secondarynamenode(self, cluster):
        return u.get_instance(cluster, 'HDFS_SECONDARYNAMENODE')

    def get_historyserver(self, cluster):
        return u.get_instance(cluster, 'YARN_JOBHISTORY')

    def get_resourcemanager(self, cluster):
        return u.get_instance(cluster, 'YARN_RESOURCEMANAGER')

    def get_nodemanagers(self, cluster):
        return u.get_instances(cluster, 'YARN_NODEMANAGER')

    def get_oozie(self, cluster):
        return u.get_instance(cluster, 'OOZIE_SERVER')

    def get_hive_metastore(self, cluster):
        return u.get_instance(cluster, 'HIVE_METASTORE')

    def get_hive_servers(self, cluster):
        return u.get_instances(cluster, 'HIVE_SERVER2')

    def get_hue(self, cluster):
        return u.get_instance(cluster, 'HUE_SERVER')

    def get_spark_historyserver(self, cluster):
        return u.get_instance(cluster, 'SPARK_YARN_HISTORY_SERVER')

    def get_zookeepers(self, cluster):
        return u.get_instances(cluster, 'ZOOKEEPER_SERVER')

    def get_hbase_master(self, cluster):
        return u.get_instance(cluster, 'HBASE_MASTER')

    def convert_process_configs(self, configs):
        p_dict = {
            "CLOUDERA": ['MANAGER'],
            "NAMENODE": ['NAMENODE'],
            "DATANODE": ['DATANODE'],
            "SECONDARYNAMENODE": ['SECONDARYNAMENODE'],
            "RESOURCEMANAGER": ['RESOURCEMANAGER'],
            "NODEMANAGER": ['NODEMANAGER'],
            "JOBHISTORY": ['JOBHISTORY'],
            "OOZIE": ['OOZIE_SERVER'],
            "HIVESERVER": ['HIVESERVER2'],
            "HIVEMETASTORE": ['HIVEMETASTORE'],
            "WEBHCAT": ['WEBHCAT'],
            "HUE": ['HUE_SERVER'],
            "SPARK_ON_YARN": ['SPARK_YARN_HISTORY_SERVER'],
            "ZOOKEEPER": ['SERVER'],
            "MASTER": ['MASTER'],
            "REGIONSERVER": ['REGIONSERVER']
        }
        if isinstance(configs, res.Resource):
            configs = configs.to_dict()
        for k in configs.keys():
            if k in p_dict.keys():
                item = configs[k]
                del configs[k]
                newkey = p_dict[k][0]
                configs[newkey] = item
        return res.Resource(configs)

    def convert_role_showname(self, showname):
        name_dict = {
            'CLOUDERA_MANAGER': 'MANAGER',
            'HDFS_NAMENODE': 'NAMENODE',
            'HDFS_DATANODE': 'DATANODE',
            'HDFS_SECONDARYNAMENODE': 'SECONDARYNAMENODE',
            'YARN_RESOURCEMANAGER': 'RESOURCEMANAGER',
            'YARN_NODEMANAGER': 'NODEMANAGER',
            'YARN_JOBHISTORY': 'JOBHISTORY',
            'OOZIE_SERVER': 'OOZIE_SERVER',
            'HIVE_SERVER2': 'HIVESERVER2',
            'HIVE_METASTORE': 'HIVEMETASTORE',
            'HIVE_WEBHCAT': 'WEBHCAT',
            'HUE_SERVER': 'HUE_SERVER',
            'SPARK_YARN_HISTORY_SERVER': 'SPARK_YARN_HISTORY_SERVER',
            'ZOOKEEPER_SERVER': 'SERVER',
            'HBASE_MASTER': 'MASTER',
            'HBASE_REGIONSERVER': 'REGIONSERVER',
            'FLUME_AGENT': 'AGENT',
            'IMPALA_CATALOGSERVER': 'CATALOGSERVER',
            'IMPALA_STATESTORE': 'STATESTORE',
            'IMPALAD': 'IMPALAD',
            'KEY_VALUE_STORE_INDEXER': 'HBASE_INDEXER',
            'SENTRY_SERVER': 'SENTRY_SERVER',
            'SOL_SERVER': 'SOLR_SERVER',
            'SQOOP_SERVER': 'SQOOP_SERVER',
        }
        return name_dict.get(showname, showname)

    def install_packages(self, instances, packages):
        # instances non-empty
        cpo.add_provisioning_step(
            instances[0].cluster_id, _("Install packages"), len(instances))

        with context.ThreadGroup() as tg:
            for i in instances:
                tg.spawn('cdh-inst-pkgs-%s' % i.instance_name,
                         self._install_pkgs, i, packages)

    @cpo.event_wrapper(True)
    def _install_pkgs(self, instance, packages):
        with instance.remote() as r:
            cmd.install_packages(r, packages)

    def start_cloudera_agents(self, instances):
        # instances non-empty
        cpo.add_provisioning_step(
            instances[0].cluster_id, _("Start Cloudera Agents"),
            len(instances))

        with context.ThreadGroup() as tg:
            for i in instances:
                tg.spawn('cdh-agent-start-%s' % i.instance_name,
                         self._start_cloudera_agent, i)

    @cpo.event_wrapper(True)
    def _start_cloudera_agent(self, instance):
        mng_hostname = self.get_manager(instance.cluster).hostname()
        with instance.remote() as r:
            cmd.start_ntp(r)
            cmd.configure_agent(r, mng_hostname)
            cmd.start_agent(r)

    def configure_swift(self, cluster, instances=None):
        if self.c_helper.is_swift_enabled(cluster):
            if not instances:
                instances = u.get_instances(cluster)
            cpo.add_provisioning_step(
                cluster.id, _("Configure Swift"), len(instances))

            with context.ThreadGroup() as tg:
                for i in instances:
                    tg.spawn('cdh-swift-conf-%s' % i.instance_name,
                             self._configure_swift_to_inst, i)

    @cpo.event_wrapper(True)
    def _configure_swift_to_inst(self, instance):
        cluster = instance.cluster
        with instance.remote() as r:
            r.execute_command('sudo curl %s -o %s/hadoop-openstack.jar' % (
                self.c_helper.get_swift_lib_url(cluster), HADOOP_LIB_DIR))

    def put_hive_hdfs_xml(self, cluster):
        servers = self.get_hive_servers(cluster)
        with servers[0].remote() as r:
            conf_path = edp_u.get_hive_shared_conf_path('hdfs')
            r.execute_command(
                'sudo su - -c "hadoop fs -mkdir -p %s" hdfs'
                % os.path.dirname(conf_path))
            r.execute_command(
                'sudo su - -c "hadoop fs -put /etc/hive/conf/hive-site.xml '
                '%s" hdfs' % conf_path)

    def configure_hive(self, cluster):
        manager = self.get_manager(cluster)
        with manager.remote() as r:
            self.db_helper.create_hive_database(cluster, r)

    def create_hive_hive_directory(self, cluster):
        # Hive requires /tmp/hive-hive directory
        namenode = self.get_namenode(cluster)
        with namenode.remote() as r:
            r.execute_command(
                'sudo su - -c "hadoop fs -mkdir -p /tmp/hive-hive" hdfs')
            r.execute_command(
                'sudo su - -c "hadoop fs -chown hive /tmp/hive-hive" hdfs')

    def install_extjs(self, cluster):
        extjs_remote_location = self.c_helper.get_extjs_lib_url(cluster)
        extjs_vm_location_dir = '/var/lib/oozie'
        extjs_vm_location_path = extjs_vm_location_dir + '/extjs.zip'
        with self.get_oozie(cluster).remote() as r:
            if r.execute_command('ls %s/ext-2.2' % extjs_vm_location_dir,
                                 raise_when_error=False)[0] != 0:
                r.execute_command('curl -L -o \'%s\' %s' % (
                    extjs_vm_location_path,  extjs_remote_location),
                    run_as_root=True)
                r.execute_command('unzip %s -d %s' % (
                    extjs_vm_location_path, extjs_vm_location_dir),
                    run_as_root=True)

    @cpo.event_wrapper(
        True, step=_("Start Cloudera manager"), param=('cluster', 1))
    def start_cloudera_manager(self, cluster):
        manager = self.get_manager(cluster)
        with manager.remote() as r:
            cmd.start_cloudera_db(r)
            cmd.start_manager(r)

        timeout = 300
        LOG.debug("Waiting {timeout} seconds for Manager to start: "
                  .format(timeout=timeout))
        s_time = timeutils.utcnow()
        while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
            try:
                conn = telnetlib.Telnet(manager.management_ip, CM_API_PORT)
                conn.close()
                break
            except IOError:
                context.sleep(2)
        else:
            message = _("Cloudera Manager failed to start in %(timeout)s "
                        "minutes on node '%(node)s' of cluster "
                        "'%(cluster)s'") % {
                            'timeout': timeout / 60,
                            'node': manager.management_ip,
                            'cluster': cluster.name}
            raise ex.HadoopProvisionError(message)

        LOG.info(_LI("Cloudera Manager has been started"))

    def configure_os(self, instances):
        # instances non-empty
        cpo.add_provisioning_step(
            instances[0].cluster_id, _("Configure OS"), len(instances))
        with context.ThreadGroup() as tg:
            for inst in instances:
                tg.spawn('cdh-repo-conf-%s' % inst.instance_name,
                         self._configure_repo_from_inst, inst)

    @cpo.event_wrapper(True)
    def _configure_repo_from_inst(self, instance):
        LOG.debug("Configure repos from instance {instance}".format(
                  instance=instance.instance_name))
        cluster = instance.cluster

        cdh5_key = self.c_helper.get_cdh5_key_url(cluster)
        cm5_key = self.c_helper.get_cm5_key_url(cluster)

        with instance.remote() as r:
            if cmd.is_ubuntu_os(r):
                cdh5_key = (cdh5_key or
                            self.c_helper.DEFAULT_CDH5_UBUNTU_REPO_KEY_URL)
                cm5_key = (cm5_key or
                           self.c_helper.DEFAULT_CM5_UBUNTU_REPO_KEY_URL)

                cdh5_repo_content = self.c_helper.CDH5_UBUNTU_REPO
                cm5_repo_content = self.c_helper.CM5_UBUNTU_REPO

                cmd.write_ubuntu_repository(r, cdh5_repo_content, 'cdh')
                cmd.add_apt_key(r, cdh5_key)
                cmd.write_ubuntu_repository(r, cm5_repo_content, 'cm')
                cmd.add_apt_key(r, cm5_key)
                cmd.update_repository(r)

            if cmd.is_centos_os(r):
                cdh5_repo_content = self.c_helper.CDH5_CENTOS_REPO
                cm5_repo_content = self.c_helper.CM5_CENTOS_REPO

                cmd.write_centos_repository(r, cdh5_repo_content, 'cdh')
                cmd.write_centos_repository(r, cm5_repo_content, 'cm')
                cmd.update_repository(r)
