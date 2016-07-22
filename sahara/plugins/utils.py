# Copyright (c) 2013 Mirantis Inc.
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

import itertools

from oslo_utils import netutils
from six.moves.urllib import parse as urlparse

from sahara.i18n import _
from sahara.plugins import base as plugins_base
from sahara.plugins import exceptions as ex


def get_node_groups(cluster, node_process=None):
    return [ng for ng in cluster.node_groups
            if (node_process is None or
                node_process in ng.node_processes)]


def get_instances_count(cluster, node_process=None):
    return sum([ng.count for ng in get_node_groups(cluster, node_process)])


def get_instances(cluster, node_process=None):
    nodes = get_node_groups(cluster, node_process)
    return list(itertools.chain(*[node.instances for node in nodes]))


def get_instance(cluster, node_process):
    instances = get_instances(cluster, node_process)
    if len(instances) > 1:
        raise ex.InvalidComponentCountException(
            node_process, _('0 or 1'), len(instances))
    return instances[0] if instances else None


def generate_host_names(nodes):
    return "\n".join([n.hostname() for n in nodes])


def generate_fqdn_host_names(nodes):
    return "\n".join([n.fqdn() for n in nodes])


def get_port_from_address(address):
    parse_result = urlparse.urlparse(address)
    # urlparse do not parse values like 0.0.0.0:8000,
    # netutils do not parse values like http://localhost:8000,
    # so combine approach is using
    if parse_result.port:
        return parse_result.port
    else:
        return netutils.parse_host_port(address)[1]


def instances_with_services(instances, node_processes):
    node_processes = set(node_processes)
    return list(filter(
        lambda x: node_processes.intersection(
            x.node_group.node_processes), instances))


def start_process_event_message(process):
    return _("Start the following process(es): {process}").format(
        process=process)


def get_config_value_or_default(
        service=None, name=None, cluster=None, config=None):
    if not config:
        if not service or not name:
            raise RuntimeError(_("Unable to retrieve config details"))
        default_value = None
    else:
        service = config.applicable_target
        name = config.name
        default_value = config.default_value

    cluster_configs = cluster.cluster_configs
    if cluster_configs.get(service, {}).get(name, None) is not None:
        return cluster_configs.get(service, {}).get(name, None)

    # Try getting config from the cluster.
    for ng in cluster.node_groups:
        if (ng.configuration().get(service) and
                ng.configuration()[service].get(name)):
            return ng.configuration()[service][name]

    # Find and return the default
    if default_value is not None:
        return default_value

    plugin = plugins_base.PLUGINS.get_plugin(cluster.plugin_name)
    configs = plugin.get_all_configs(cluster.hadoop_version)

    for config in configs:
        if config.applicable_target == service and config.name == name:
            return config.default_value

    raise RuntimeError(_("Unable to get parameter '%(param_name)s' from "
                         "service %(service)s"),
                       {'param_name': name, 'service': service})
