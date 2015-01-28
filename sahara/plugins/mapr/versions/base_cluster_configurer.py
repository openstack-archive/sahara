# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import abc
import collections as c
import os

from oslo_log import log as logging
import six

from sahara.i18n import _LI
import sahara.plugins.mapr.util.cluster_helper as ch
import sahara.plugins.mapr.util.cluster_info as ci
from sahara.plugins.mapr.util import config
import sahara.plugins.mapr.util.config_file_utils as cfu
import sahara.plugins.mapr.util.dict_utils as du
import sahara.plugins.mapr.versions.version_handler_factory as vhf
import sahara.plugins.utils as u
import sahara.swift.swift_helper as sh


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseClusterConfigurer(object):

    def get_topology_configs(self):
        result = c.defaultdict(dict)
        if config.is_data_locality_enabled(self.cluster):
            if self.is_node_awareness_enabled():
                LOG.debug('Node group awareness is set to True')

                file_name = '%s/core-site.xml' % self.get_hadoop_conf_dir()
                service = self.plugin_spec.get_service_for_file_name(file_name)
                data = {}
                data['net.topology.impl'] = (
                    'org.apache.hadoop.net.NetworkTopologyWithNodeGroup')
                data['net.topology.nodegroup.aware'] = True
                data['dfs.block.replicator.classname'] = (
                    'org.apache.hadoop.hdfs.server.namenode'
                    '.BlockPlacementPolicyWithNodeGroup')
                result[service][file_name] = data

                file_name = '%s/mapred-site.xml' % self.get_hadoop_conf_dir()
                service = self.plugin_spec.get_service_for_file_name(file_name)
                data = {}
                data['mapred.jobtracker.nodegroup.aware'] = True
                data['mapred.task.cache.levels'] = 3
                result[service][file_name] = data

                file_name = '/opt/mapr/conf/cldb.conf'
                service = self.plugin_spec.get_service_for_file_name(file_name)
                data = {}
                data['net.topology.script.file.name'] = '/opt/mapr/topology.sh'
                result[service][file_name] = data
            else:
                LOG.debug('Node group awareness is not implemented in YARN'
                          ' yet so enable_hypervisor_awareness set to'
                          ' False explicitly')
        return result

    def get_swift_configs(self):
        mapper = lambda i: (i['name'], i['value'])
        file_name = '%s/core-site.xml' % self.get_hadoop_conf_dir()
        service = self.plugin_spec.get_service_for_file_name(file_name)
        data = dict(map(mapper, sh.get_swift_configs()))
        return {service: {file_name: data}}

    def get_cluster_configs(self):
        default_configs = self.cluster_info.get_default_configs()
        user_configs = self.cluster_info.get_user_configs()
        result = du.deep_update(default_configs, user_configs)
        file_name = '/opt/mapr/conf/cldb.conf'
        service = self.plugin_spec.get_service_for_file_name(file_name)
        if file_name not in result[service]:
            result[service][file_name] = {}
        data = result[service][file_name]
        data['cldb.zookeeper.servers'] = ch.get_zookeeper_nodes_ip_with_port(
            self.cluster)
        return result

    def get_cluster_configs_template(self):
        template = {}
        du.deep_update(template, self.get_topology_configs(), False)
        du.deep_update(template, self.get_swift_configs(), False)
        du.deep_update(template, self.get_cluster_configs(), False)
        return template

    def get_node_group_configs(self, node_groups=None):
        ng_configs = {}
        if not node_groups:
            node_groups = self.cluster.node_groups
        cc_template = self.cluster_configs_template
        p_spec = self.plugin_spec
        for ng in node_groups:
            ng_services = self.cluster_info.get_services(ng)
            d_configs = dict(filter(lambda i: i[0] in ng_services,
                                    six.iteritems(cc_template)))
            u_configs = self.cluster_info.get_user_configs(ng)
            nc_template = du.deep_update(d_configs, u_configs)
            nc_data = {}
            for files in nc_template.values():
                for f_name, f_data in six.iteritems(files):
                    if f_name:
                        f_type = p_spec.get_file_type(f_name)
                        f_content = cfu.to_file_content(f_data, f_type)
                        if f_content:
                            nc_data[f_name] = f_content
            ng_configs[ng.id] = nc_data
        return ng_configs

    def configure_instances(self, instances=None):
        if not instances:
            instances = u.get_instances(self.cluster)
        for i in instances:
            i_files = self.node_group_files[i.node_group_id]
            LOG.info(_LI('Writing files %(f_names)s to node %(node)s'),
                     {'f_names': i_files.keys(), 'node': i.management_ip})
            with i.remote() as r:
                for f_name in i_files:
                    r.execute_command('mkdir -p ' + os.path.dirname(f_name),
                                      run_as_root=True)
                    LOG.debug('Created dir: %s', os.path.dirname(f_name))
                r.write_files_to(i_files, run_as_root=True)
            config.post_configure_instance(i)

    def __init__(self, cluster, plugin_spec):
        h_version = cluster.hadoop_version
        v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
        self.context = v_handler.get_context(cluster)
        self.cluster = cluster
        self.plugin_spec = plugin_spec
        self.cluster_info = ci.ClusterInfo(self.cluster, self.plugin_spec)
        self.cluster_configs_template = self.get_cluster_configs_template()
        self.node_group_files = self.get_node_group_configs()

    def configure(self, instances=None):
        self.configure_topology_data(self.cluster)
        self.configure_instances(instances)

    @staticmethod
    def _post_configure_instance(instance):
        config.post_configure_instance(instance)

    def configure_topology_data(self, cluster):
        config.configure_topology_data(
            cluster, self.is_node_awareness_enabled())

    @abc.abstractmethod
    def get_hadoop_conf_dir(self):
        return

    @abc.abstractmethod
    def is_node_awareness_enabled(self):
        return
