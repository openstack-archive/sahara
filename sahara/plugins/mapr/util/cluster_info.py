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

import collections as c

import six

import sahara.plugins.utils as u


class ClusterInfo(object):

    # TODO(aosadchiy): perform lookup for plugin_spec

    def __init__(self, cluster, plugin_spec):
        self.cluster = cluster
        self.plugin_spec = plugin_spec

    def get_default_configs(self, node_group=None):
        services = self.get_services(node_group)
        return self.plugin_spec.get_default_plugin_configs(services)

    def get_services(self, node_group=None):
        if not node_group:
            return set(service for node_group in self.cluster.node_groups
                       for service in self.get_services(node_group))
        else:
            return (set(self.plugin_spec.get_node_process_service(node_process)
                        for node_process in node_group.node_processes)
                    | set(['general']))

    def get_user_configs(self, node_group=None):
        services = self.get_services(node_group)
        predicate = lambda i: i[0] in services and i[1]
        configs = dict(filter(
            predicate, six.iteritems(self.cluster.cluster_configs)))
        scope = 'node' if node_group else 'cluster'
        result = c.defaultdict(lambda: c.defaultdict(dict))
        for service, kv in six.iteritems(configs):
            for key, value in six.iteritems(kv):
                filename = self.plugin_spec.get_config_file(
                    scope, service, key)
                result[service][filename][key] = value
        return result

    def get_node_group_files(self):
        return

    def get_node_groups(self, node_process=None):
        return u.get_node_groups(self.cluster, node_process)

    def get_instances_count(self, node_process=None):
        return u.get_instances_count(self.cluster, node_process)

    def get_instances(self, node_process=None):
        return u.get_instances(self.cluster, node_process)

    def get_instance(self, node_process):
        return u.get_instance(self.cluster, node_process)

    def get_instances_ip(self, node_process):
        return [i.management_ip for i in self.get_instances(node_process)]

    def get_instance_ip(self, node_process):
        return self.get_instance(node_process).management_ip
