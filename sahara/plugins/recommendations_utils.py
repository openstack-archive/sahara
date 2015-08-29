# Copyright (c) 2015 Mirantis Inc.
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

import abc

from oslo_log import log as logging
import six

from sahara import conductor as cond
from sahara import context
from sahara.utils.openstack import nova

conductor = cond.API

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AutoConfigsProvider(object):
    def __init__(self, mapper, plugin_configs, cluster, scaling):
        """This meta class provides general recommendation utils for cluster

        configuration.
        :param mapper: dictionary, that describes which cluster configs and
        node_configs to configure. It should maps to following dicts:
        node_configs to configure and cluster_configs to configure. This
        dicts should contains abstract names of configs as keys and
        tuple (correct_applicable_target, correct_name) as values. Such
        representation allows to use same AutoConfigsProvider for plugins
        with almost same configs and configuring principles.
        :param plugin_configs: all plugins_configs for specified plugin
        :param cluster: cluster which is required to configure
        :param scaling: indicates that current cluster operation is scaling
        """
        self.plugin_configs = plugin_configs
        self.cluster = cluster
        self.node_configs_to_update = mapper.get('node_configs', {})
        self.cluster_configs_to_update = mapper.get('cluster_configs', {})
        self.scaling = scaling

    @abc.abstractmethod
    def _get_recommended_node_configs(self, node_group):
        """Method calculates and returns recommended configs for node_group.

        It's not required to update node_configs of node_group using the
        conductor api in this method, because it will be done in the method
        apply_node_configs.

        :param node_group: NodeGroup Sahara resource.
        :return: dictionary with calculated recommended configs for
        node_group.
        """
        pass

    @abc.abstractmethod
    def _get_recommended_cluster_configs(self):
        """Method calculates and returns recommended configs for cluster.

        It's not required to update cluster_configs of cluster using the
        conductor api in this method, because it will be done in the method
        apply_cluster_configs.

        :return: dictionary with calculated recommended configs for
        cluster.
        """
        pass

    def _can_be_recommended(self, configs_list, node_group=None):
        """Method calculates and returns True, when it's possible to

        automatically configure provided list of configs configs_list.
        Otherwise, method should return False.

        :param configs_list: list of configs which we want to configure
        :param node_group: optional argument, which should be provided if
        some config can be used in node_configs of some node_group
        :return: True if all configs can be configured and False otherwise
        """
        # cluster configs is Frozen Dict, so let's call to_dict()
        cl_configs = self.cluster.cluster_configs.to_dict()
        for ncfg in configs_list:
            section, name = self._get_correct_section_and_name(ncfg)
            if section in cl_configs and name in cl_configs[section]:
                return False

        if not node_group:
            return True

        cl_configs = node_group.node_configs.to_dict()
        for ncfg in configs_list:
            section, name = self._get_correct_section_and_name(ncfg)
            if section in cl_configs and name in cl_configs[section]:
                return False
        return True

    def _get_correct_section_and_name(self, config_name):
        """Calculates and returns correct applicable target and name from

        abstract name of config.
        :param config_name: abstract name of config.
        :return: correct applicable target and name for config_name
        """
        section, name = None, None
        if config_name in self.cluster_configs_to_update:
            section = self.cluster_configs_to_update[config_name][0]
            name = self.cluster_configs_to_update[config_name][1]
        elif config_name in self.node_configs_to_update:
            section = self.node_configs_to_update[config_name][0]
            name = self.node_configs_to_update[config_name][1]
        return section, name

    def _get_default_config_value(self, config_name):
        """Calculates and return default value of config from

        abstract name of config.
        :param config_name: abstract name of config.
        :return: default config value for config_name.
        """
        section, name = self._get_correct_section_and_name(config_name)
        for config in self.plugin_configs:
            if config.applicable_target == section and config.name == name:
                return config.default_value

    def _merge_configs(self, current_configs, proposed_configs):
        """Correctly merges old configs and new extra configs"""
        result = {}
        for (section, configs) in six.iteritems(proposed_configs):
            cfg_values = {}
            if section in current_configs:
                cfg_values = (current_configs[section] if
                              current_configs[section] else {})
            cfg_values.update(configs)
            result.update({section: cfg_values})
        for (section, configs) in six.iteritems(current_configs):
            if section not in result:
                result.update({section: configs})
        return result

    def _get_cluster_extra(self):
        cluster = self.cluster
        return cluster.extra.to_dict() if cluster.extra else {}

    def finalize_autoconfiguration(self):
        if not self.cluster.use_autoconfig:
            return
        cluster_extra = self._get_cluster_extra()
        cluster_extra['auto-configured'] = True
        conductor.cluster_update(
            context.ctx(), self.cluster, {'extra': cluster_extra})

    def apply_node_configs(self, node_group):
        """Method applies configs for node_group using conductor api,

        which were calculated with recommend_node_configs method.
        :param node_group: NodeGroup Sahara resource.
        :return: None.
        """
        if not node_group.use_autoconfig or not self.cluster.use_autoconfig:
            return
        to_update = self.node_configs_to_update
        recommended_node_configs = self._get_recommended_node_configs(
            node_group)
        if not recommended_node_configs:
            # Nothing to configure
            return
        current_dict = node_group.node_configs.to_dict()
        configuration = {}
        for ncfg in six.iterkeys(to_update):
            if ncfg not in recommended_node_configs:
                continue
            n_section = to_update[ncfg][0]
            n_name = to_update[ncfg][1]
            proposed_config_value = recommended_node_configs[ncfg]
            if n_section not in configuration:
                configuration.update({n_section: {}})
            configuration[n_section].update({n_name: proposed_config_value})
        current_dict = self._merge_configs(current_dict, configuration)
        conductor.node_group_update(context.ctx(), node_group,
                                    {'node_configs': current_dict})

    def apply_cluster_configs(self):
        """Method applies configs for cluster using conductor api, which were

        calculated with recommend_cluster_configs method.
        :return: None.
        """
        cluster = self.cluster
        if not cluster.use_autoconfig:
            return
        to_update = self.cluster_configs_to_update
        recommended_cluster_configs = self._get_recommended_cluster_configs()
        if not recommended_cluster_configs:
            # Nothing to configure
            return
        current_dict = cluster.cluster_configs.to_dict()
        configuration = {}
        for ncfg in six.iterkeys(to_update):
            if ncfg not in recommended_cluster_configs:
                continue
            n_section = to_update[ncfg][0]
            n_name = to_update[ncfg][1]
            proposed_config_value = recommended_cluster_configs[ncfg]
            if n_section not in configuration:
                configuration.update({n_section: {}})
            configuration[n_section].update({n_name: proposed_config_value})
        current_dict = self._merge_configs(current_dict, configuration)
        conductor.cluster_update(context.ctx(), cluster,
                                 {'cluster_configs': current_dict})

    def apply_recommended_configs(self):
        """Method applies recommended configs for cluster and for all

        node_groups using conductor api.
        :return: None.
        """
        if self.scaling:
            # Validate cluster is not an old created cluster
            cluster_extra = self._get_cluster_extra()
            if 'auto-configured' not in cluster_extra:
                # Don't configure
                return

        for ng in self.cluster.node_groups:
            self.apply_node_configs(ng)
        self.apply_cluster_configs()
        configs = list(self.cluster_configs_to_update.keys())
        configs.extend(list(self.node_configs_to_update.keys()))
        LOG.debug("Following configs were auto-configured: {configs}".format(
            configs=configs))
        self.finalize_autoconfiguration()


class HadoopAutoConfigsProvider(AutoConfigsProvider):
    def __init__(self, mapper, plugin_configs, cluster, scaling, hbase=False):
        super(HadoopAutoConfigsProvider, self).__init__(
            mapper, plugin_configs, cluster, scaling)
        self.requested_flavors = {}
        self.is_hbase_enabled = hbase

    def _get_java_opts(self, value):
        return "-Xmx%dm" % int(value)

    def _transform_mb_to_gb(self, mb):
        return mb / 1024.

    def _transform_gb_to_mb(self, gb):
        return gb * 1024.

    def _get_min_size_of_container(self, ram):
        if ram <= 4:
            return 256
        if ram <= 8:
            return 512
        if ram <= 24:
            return 1024
        return 2048

    def _get_os_ram_recommendation(self, ram):
        upper_bounds = [4, 8, 16, 24, 48, 64, 72, 96, 128, 256]
        reserve_for_os = [1, 2, 2, 4, 6, 8, 8, 12, 24, 32]
        for (upper, reserve) in zip(upper_bounds, reserve_for_os):
            if ram <= upper:
                return reserve
        return 64

    def _get_hbase_ram_recommendations(self, ram):
        if not self.is_hbase_enabled:
            return 0
        upper_bounds = [4, 8, 16, 24, 48, 64, 72, 96, 128, 256]
        reserve_for_hbase = [1, 1, 2, 4, 8, 8, 8, 16, 24, 32]
        for (upper, reserve) in zip(upper_bounds, reserve_for_hbase):
            if ram <= upper:
                return reserve
        return 64

    def _get_node_group_data(self, node_group):
        if node_group.flavor_id not in self.requested_flavors:
            flavor = nova.get_flavor(id=node_group.flavor_id)
            self.requested_flavors[node_group.flavor_id] = flavor
        else:
            flavor = self.requested_flavors[node_group.flavor_id]
        cpu = flavor.vcpus
        ram = flavor.ram
        data = {}
        # config recommendations was taken from Ambari code
        os = self._get_os_ram_recommendation(self._transform_mb_to_gb(ram))
        hbase = self._get_hbase_ram_recommendations(
            self._transform_mb_to_gb(ram))
        reserved_ram = self._transform_gb_to_mb(os + hbase)
        min_container_size = self._get_min_size_of_container(
            self._transform_mb_to_gb(ram))

        # we use large amount of containers to allow users to run
        # at least 4 jobs at same time on clusters based on small flavors
        data["containers"] = int(max(
            8, min(2 * cpu, ram / min_container_size)))
        data["ramPerContainer"] = (ram - reserved_ram) / data["containers"]
        data["ramPerContainer"] = max(data["ramPerContainer"],
                                      min_container_size)
        data["ramPerContainer"] = min(2048, int(data["ramPerContainer"]))

        data["ramPerContainer"] = int(data["ramPerContainer"])
        data["mapMemory"] = int(data["ramPerContainer"])
        data["reduceMemory"] = int(2 * data["ramPerContainer"])
        data["amMemory"] = int(min(data["mapMemory"], data["reduceMemory"]))

        return data

    def _get_recommended_node_configs(self, node_group):
        """Calculates recommended MapReduce and YARN configs for specified

        node_group.
        :param node_group: NodeGroup Sahara resource
        :return: dictionary with recommended MapReduce and YARN configs
        """
        configs_to_update = list(self.node_configs_to_update.keys())
        if not self._can_be_recommended(configs_to_update, node_group):
            return {}
        data = self._get_node_group_data(node_group)
        r = {}
        r['yarn.nodemanager.resource.memory-mb'] = (data['containers'] *
                                                    data['ramPerContainer'])
        r['yarn.scheduler.minimum-allocation-mb'] = data['ramPerContainer']
        r['yarn.scheduler.maximum-allocation-mb'] = (data['containers'] *
                                                     data['ramPerContainer'])
        r['yarn.nodemanager.vmem-check-enabled'] = "false"
        r['yarn.app.mapreduce.am.resource.mb'] = data['amMemory']
        r['yarn.app.mapreduce.am.command-opts'] = self._get_java_opts(
            0.8 * data['amMemory'])
        r['mapreduce.map.memory.mb'] = data['mapMemory']
        r['mapreduce.reduce.memory.mb'] = data['reduceMemory']
        r['mapreduce.map.java.opts'] = self._get_java_opts(
            0.8 * data['mapMemory'])
        r['mapreduce.reduce.java.opts'] = self._get_java_opts(
            0.8 * data['reduceMemory'])
        r['mapreduce.task.io.sort.mb'] = int(min(
            0.4 * data['mapMemory'], 1024))
        return r

    def get_datanode_name(self):
        return "datanode"

    def _get_recommended_cluster_configs(self):
        """Method recommends dfs_replication for cluster.

        :return: recommended value of dfs_replication.
        """
        if not self._can_be_recommended(['dfs.replication']):
            return {}
        datanode_count = 0
        datanode_proc_name = self.get_datanode_name()
        for ng in self.cluster.node_groups:
            if datanode_proc_name in ng.node_processes:
                datanode_count += ng.count
        replica = 'dfs.replication'
        recommended_value = self._get_default_config_value(replica)
        if recommended_value:
            return {replica: min(recommended_value, datanode_count)}
        else:
            return {}
