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

import sahara.plugins.mapr.util.dict_utils as du
import sahara.plugins.mapr.util.func_utils as fu
import sahara.plugins.mapr.versions.version_handler_factory as vhf
import sahara.utils.configs as c


def get_scope_default_configs(version_handler, scope, services=None):
    configs = map(lambda i: i.to_dict(), version_handler.get_configs())
    q_predicate = fu.field_equals_predicate('scope', scope)
    if services:
        at_predicate = fu.in_predicate('applicable_target', services)
        q_predicate = fu.and_predicate(q_predicate, at_predicate)
    q_fields = ['applicable_target', 'name', 'default_value']
    q_result = du.select(q_fields, configs, q_predicate)
    m_reducer = du.iterable_to_values_pair_dict_reducer(
        'name', 'default_value')
    return du.map_by_field_value(q_result, 'applicable_target',
                                 dict, m_reducer)


def get_cluster_default_configs(version_handler, services=None):
    return get_scope_default_configs(version_handler, 'cluster', services)


def get_node_default_configs(version_handler, services=None):
    return get_scope_default_configs(version_handler, 'node', services)


def get_default_configs(version_handler, services=None):
    cluster_configs = get_cluster_default_configs(version_handler, services)
    node_configs = get_node_default_configs(version_handler, services)
    return c.merge_configs(cluster_configs, node_configs)


def get_node_group_services(node_group):
    h_version = node_group.cluster.hadoop_version
    v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
    services = v_handler.get_node_processes()
    node_processes = node_group.node_processes
    return set(s for np in node_processes
               for s in services if np in services[s])


def get_cluster_configs(cluster):
    h_version = cluster.hadoop_version
    v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
    default_configs = get_cluster_default_configs(v_handler)
    user_configs = cluster.cluster_configs
    return c.merge_configs(default_configs, user_configs)


def get_configs(node_group):
    services = get_node_group_services(node_group)
    h_version = node_group.cluster.hadoop_version
    v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
    default_configs = get_default_configs(v_handler, services)
    user_configs = node_group.configuration()
    return c.merge_configs(default_configs, user_configs)


def get_service(version_handler, node_process):
    node_processes = version_handler.get_node_processes()
    return du.get_keys_by_value_2(node_processes, node_process)
