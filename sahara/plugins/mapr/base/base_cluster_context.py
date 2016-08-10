# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import collections

from oslo_config import cfg

import sahara.exceptions as e
from sahara.i18n import _
import sahara.plugins.mapr.abstract.cluster_context as cc
import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.distro as distro
import sahara.plugins.mapr.services.management.management as mng
import sahara.plugins.mapr.services.maprfs.maprfs as mfs
import sahara.plugins.mapr.services.oozie.oozie as oozie
from sahara.plugins.mapr.services.swift import swift
import sahara.plugins.mapr.services.yarn.yarn as yarn
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.service_utils as su
import sahara.plugins.utils as u
from sahara.topology import topology_helper as th
import sahara.utils.configs as sahara_configs

CONF = cfg.CONF
CONF.import_opt("enable_data_locality", "sahara.topology.topology_helper")


class BaseClusterContext(cc.AbstractClusterContext):
    ubuntu_base = 'http://package.mapr.com/releases/v%s/ubuntu/ mapr optional'
    centos_base = 'http://package.mapr.com/releases/v%s/redhat/'

    def __init__(self, cluster, version_handler, added=None, removed=None):
        self._cluster = cluster
        self._distro = None
        self._distro_version = None
        self._all_services = version_handler.get_services()
        self._required_services = version_handler.get_required_services()
        self._cluster_services = None
        self._mapr_home = '/opt/mapr'
        self._name_node_uri = 'maprfs:///'
        self._cluster_mode = None
        self._node_aware = None
        self._oozie_server_uri = None
        self._oozie_server = None
        self._oozie_http = None
        self._some_instance = None
        self._configure_sh_path = None
        self._configure_sh = None
        self._mapr_db = None
        self._hadoop_home = None
        self._hadoop_version = None
        self._added_instances = added or []
        self._removed_instances = removed or []
        self._changed_instances = (
            self._added_instances + self._removed_instances)
        self._existing_instances = [i for i in self.get_instances()
                                    if i not in self._changed_instances]
        self._restart = collections.defaultdict(list)
        self._ubuntu_base_repo = None
        self._ubuntu_ecosystem_repo = None
        self._centos_base_repo = None
        self._centos_ecosystem_repo = None
        self._repos = {}
        self._is_prebuilt = None
        self._local_repo = '/opt/mapr-repository'
        self._mapr_version = None

    @property
    def cluster(self):
        return self._cluster

    @property
    def cluster_services(self):
        if not self._cluster_services:
            self._cluster_services = self.get_cluster_services()
        return self._cluster_services

    @property
    def required_services(self):
        return self._required_services

    @property
    def all_services(self):
        return self._all_services

    @property
    def mapr_home(self):
        return self._mapr_home

    @property
    def hadoop_version(self):
        return self._hadoop_version

    @property
    def hadoop_home(self):
        if not self._hadoop_home:
            f = '%(mapr_home)s/hadoop/hadoop-%(hadoop_version)s'
            args = {
                'mapr_home': self.mapr_home,
                'hadoop_version': self.hadoop_version,
            }
            self._hadoop_home = f % args
        return self._hadoop_home

    @property
    def name_node_uri(self):
        return self._name_node_uri

    @property
    def oozie_server_uri(self):
        if not self._oozie_server_uri:
            oozie_http = self.oozie_http
            url = 'http://%s/oozie' % oozie_http if oozie_http else None
            self._oozie_server_uri = url
        return self._oozie_server_uri

    @property
    def oozie_server(self):
        if not self._oozie_server:
            self._oozie_server = self.get_instance(oozie.OOZIE)
        return self._oozie_server

    @property
    def oozie_http(self):
        if not self._oozie_http:
            oozie_server = self.oozie_server
            ip = oozie_server.management_ip if oozie_server else None
            self._oozie_http = '%s:11000' % ip if ip else None
        return self._oozie_http

    @property
    def cluster_mode(self):
        return self._cluster_mode

    @property
    def is_node_aware(self):
        return self._node_aware and CONF.enable_data_locality

    @property
    def some_instance(self):
        if not self._some_instance:
            self._some_instance = self.cluster.node_groups[0].instances[0]
        return self._some_instance

    @property
    def distro_version(self):
        if not self._distro_version:
            self._distro_version = distro.get_version(self.some_instance)
        return self._distro_version

    @property
    def distro(self):
        if not self._distro:
            self._distro = distro.get(self.some_instance)
        return self._distro

    @property
    def mapr_db(self):
        if self._mapr_db is None:
            mapr_db = mfs.MapRFS.ENABLE_MAPR_DB_CONFIG
            mapr_db = self._get_cluster_config_value(mapr_db)
            self._mapr_db = '-noDB' if not mapr_db else ''
        return self._mapr_db

    @property
    def configure_sh_path(self):
        if not self._configure_sh_path:
            self._configure_sh_path = '%s/server/configure.sh' % self.mapr_home
        return self._configure_sh_path

    @property
    def configure_sh(self):
        if not self._configure_sh:
            f = ('%(script_path)s'
                 ' -N %(cluster_name)s'
                 ' -C %(cldbs)s'
                 ' -Z %(zookeepers)s'
                 ' -no-autostart -f %(m7)s')
            args = {
                'script_path': self.configure_sh_path,
                'cluster_name': self.cluster.name,
                'cldbs': self.get_cldb_nodes_ip(),
                'zookeepers': self.get_zookeeper_nodes_ip(),
                'm7': self.mapr_db
            }
            self._configure_sh = f % args
        return self._configure_sh

    def _get_cluster_config_value(self, config):
        cluster_configs = self.cluster.cluster_configs
        service = config.applicable_target
        name = config.name
        if service in cluster_configs and name in cluster_configs[service]:
            return cluster_configs[service][name]
        else:
            return config.default_value

    def get_node_processes(self):
        node_processes = []
        for ng in self.cluster.node_groups:
            for np in ng.node_processes:
                if np not in node_processes:
                    node_processes.append(self.get_node_process_by_name(np))
        return node_processes

    def get_node_process_by_name(self, name):
        for service in self.cluster_services:
            for node_process in service.node_processes:
                if node_process.ui_name == name:
                    return node_process

    def get_instances(self, node_process=None):
        if node_process is not None:
            node_process = su.get_node_process_name(node_process)
        return u.get_instances(self.cluster, node_process)

    def get_instance(self, node_process):
        node_process_name = su.get_node_process_name(node_process)
        instances = u.get_instances(self.cluster, node_process_name)
        return instances[0] if instances else None

    def get_instances_ip(self, node_process):
        return [i.internal_ip for i in self.get_instances(node_process)]

    def get_instance_ip(self, node_process):
        i = self.get_instance(node_process)
        return i.internal_ip if i else None

    def get_zookeeper_nodes_ip_with_port(self, separator=','):
        return separator.join(['%s:%s' % (ip, mng.ZK_CLIENT_PORT)
                               for ip in self.get_instances_ip(mng.ZOOKEEPER)])

    def check_for_process(self, instance, process):
        return su.has_node_process(instance, process)

    def get_services_configs_dict(self, services=None):
        if not services:
            services = self.cluster_services
        result = dict()
        for service in services:
            result.update(service.get_configs_dict())
        return result

    def get_chosen_service_version(self, service_name):
        service_configs = self.cluster.cluster_configs.get(service_name, None)
        if not service_configs:
            return None
        return service_configs.get('%s Version' % service_name, None)

    def get_cluster_services(self, node_group=None):
        node_processes = None

        if node_group:
            node_processes = node_group.node_processes
        else:
            node_processes = [np for ng in self.cluster.node_groups
                              for np in ng.node_processes]
            node_processes = g.unique_list(node_processes)
        services = g.unique_list(node_processes, self.get_service)

        return services + [swift.Swift()]

    def get_service(self, node_process):
        ui_name = self.get_service_name_by_node_process(node_process)
        if ui_name is None:
            raise e.InvalidDataException(
                _('Service not found in services list'))
        version = self.get_chosen_service_version(ui_name)
        service = self._find_service_instance(ui_name, version)
        if service is None:
            raise e.InvalidDataException(_('Can not map service'))
        return service

    def _find_service_instance(self, ui_name, version):
        # if version is None, the latest service version is returned
        for service in self.all_services[::-1]:
            if service.ui_name == ui_name:
                if version is not None and service.version != version:
                    continue
                return service

    def get_service_name_by_node_process(self, node_process):
        node_process_name = su.get_node_process_name(node_process)
        for service in self.all_services:
            service_node_processes = [np.ui_name
                                      for np in service.node_processes]
            if node_process_name in service_node_processes:
                return service.ui_name

    def get_instances_count(self, node_process=None):
        if node_process is not None:
            node_process = su.get_node_process_name(node_process)
        return u.get_instances_count(self.cluster, node_process)

    def get_node_groups(self, node_process=None):
        if node_process is not None:
            node_process = su.get_node_process_name(node_process)
        return u.get_node_groups(self.cluster, node_process)

    def get_cldb_nodes_ip(self, separator=','):
        return separator.join(self.get_instances_ip(mfs.CLDB))

    def get_zookeeper_nodes_ip(self, separator=','):
        return separator.join(
            self.get_instances_ip(mng.ZOOKEEPER))

    def get_resourcemanager_ip(self):
        return self.get_instance_ip(yarn.RESOURCE_MANAGER)

    def get_historyserver_ip(self):
        return self.get_instance_ip(yarn.HISTORY_SERVER)

    def has_control_nodes(self, instances):
        for inst in instances:
            zookeepers = self.check_for_process(inst, mng.ZOOKEEPER)
            cldbs = self.check_for_process(inst, mfs.CLDB)
            if zookeepers or cldbs:
                return True
        return False

    def is_present(self, service):
        is_service_subclass = lambda s: isinstance(s, service.__class__)
        return any(is_service_subclass(s) for s in self.cluster_services)

    def filter_instances(self, instances, node_process=None, service=None):
        if node_process:
            return su.filter_by_node_process(instances, node_process)
        if service:
            return su.filter_by_service(instances, service)
        return list(instances)

    def removed_instances(self, node_process=None, service=None):
        instances = self._removed_instances
        return self.filter_instances(instances, node_process, service)

    def added_instances(self, node_process=None, service=None):
        instances = self._added_instances
        return self.filter_instances(instances, node_process, service)

    def changed_instances(self, node_process=None, service=None):
        instances = self._changed_instances
        return self.filter_instances(instances, node_process, service)

    def existing_instances(self, node_process=None, service=None):
        instances = self._existing_instances
        return self.filter_instances(instances, node_process, service)

    @property
    def should_be_restarted(self):
        return self._restart

    @property
    def mapr_repos(self):
        if not self._repos:
            self._repos = {
                "ubuntu_mapr_base_repo": self.ubuntu_base_repo,
                "ubuntu_mapr_ecosystem_repo": self.ubuntu_ecosystem_repo,
                "centos_mapr_base_repo": self.centos_base_repo,
                "centos_mapr_ecosystem_repo": self.centos_ecosystem_repo,
            }
        return self._repos

    @property
    def local_repo(self):
        return self._local_repo

    @property
    def is_prebuilt(self):
        if self._is_prebuilt is None:
            self._is_prebuilt = g.is_directory(
                self.some_instance, self.local_repo)
        return self._is_prebuilt

    @property
    def mapr_version(self):
        return self._mapr_version

    @property
    def ubuntu_base_repo(self):
        if not self._ubuntu_base_repo:
            self._ubuntu_base_repo = self.ubuntu_base % self.mapr_version
        return self._ubuntu_base_repo

    @property
    def ubuntu_ecosystem_repo(self):
        return self._ubuntu_ecosystem_repo

    @property
    def centos_base_repo(self):
        if not self._centos_base_repo:
            self._centos_base_repo = self.centos_base % self.mapr_version
        return self._centos_base_repo

    @property
    def centos_ecosystem_repo(self):
        return self._centos_ecosystem_repo

    def get_configuration(self, node_group):
        services = self.get_cluster_services(node_group)
        user_configs = node_group.configuration()
        default_configs = self.get_services_configs_dict(services)
        return sahara_configs.merge_configs(default_configs, user_configs)

    def get_config_files(self, node_group):
        services = self.get_cluster_services(node_group)
        configuration = self.get_configuration(node_group)
        instance = node_group.instances[0]

        config_files = []
        for service in services:
            service_conf_files = service.get_config_files(
                cluster_context=self,
                configs=configuration[service.ui_name],
                instance=instance,
            )
            for conf_file in service_conf_files:
                file_atr = bcf.FileAttr(conf_file.remote_path,
                                        conf_file.render(), conf_file.mode,
                                        conf_file.owner)
                config_files.append(file_atr)

        return config_files

    @property
    def topology_map(self):
        return th.generate_topology_map(self.cluster, self.is_node_aware)
