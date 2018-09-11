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
from sahara.utils import api_validator
from sahara.utils import cluster as cluster_utils
from sahara.utils import cluster_progress_ops as ops
from sahara.utils import configs as sahara_configs
from sahara.utils import crypto
from sahara.utils import files
from sahara.utils import general
from sahara.utils.openstack import nova
from sahara.utils import poll_utils
from sahara.utils import proxy
from sahara.utils import remote
from sahara.utils import rpc
from sahara.utils import types
from sahara.utils import xmlutils


event_wrapper = ops.event_wrapper


def get_node_groups(cluster, node_process=None, **kwargs):
    return [ng for ng in cluster.node_groups
            if (node_process is None or
                node_process in ng.node_processes)]


def get_instances_count(cluster, node_process=None, **kwargs):
    return sum([ng.count for ng in get_node_groups(cluster, node_process)])


def get_instances(cluster, node_process=None, **kwargs):
    nodes = get_node_groups(cluster, node_process)
    return list(itertools.chain(*[node.instances for node in nodes]))


def get_instance(cluster, node_process, **kwargs):
    instances = get_instances(cluster, node_process)
    if len(instances) > 1:
        raise ex.InvalidComponentCountException(
            node_process, _('0 or 1'), len(instances))
    return instances[0] if instances else None


def generate_host_names(nodes, **kwargs):
    return "\n".join([n.hostname() for n in nodes])


def generate_fqdn_host_names(nodes, **kwargs):
    return "\n".join([n.fqdn() for n in nodes])


def get_port_from_address(address, **kwargs):
    parse_result = urlparse.urlparse(address)
    # urlparse do not parse values like 0.0.0.0:8000,
    # netutils do not parse values like http://localhost:8000,
    # so combine approach is using
    if parse_result.port:
        return parse_result.port
    else:
        return netutils.parse_host_port(address)[1]


def instances_with_services(instances, node_processes, **kwargs):
    node_processes = set(node_processes)
    return list(filter(
        lambda x: node_processes.intersection(
            x.node_group.node_processes), instances))


def start_process_event_message(process, **kwargs):
    return _("Start the following process(es): {process}").format(
        process=process)


def get_config_value_or_default(
        service=None, name=None, cluster=None, config=None, **kwargs):
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


def cluster_get_instances(cluster, instances_ids=None, **kwargs):
    return cluster_utils.get_instances(cluster, instances_ids)


def check_cluster_exists(cluster, **kwargs):
    return cluster_utils.check_cluster_exists(cluster)


def add_provisioning_step(cluster_id, step_name, total, **kwargs):
    return ops.add_provisioning_step(cluster_id, step_name, total)


def add_successful_event(instance, **kwargs):
    ops.add_successful_event(instance)


def add_fail_event(instance, exception, **kwargs):
    ops.add_fail_event(instance, exception)


def merge_configs(config_a, config_b, **kwargs):
    return sahara_configs.merge_configs(config_a, config_b)


def generate_key_pair(key_length=2048, **kwargs):
    return crypto.generate_key_pair(key_length)


def get_file_text(file_name, package='sahara', **kwargs):
    return files.get_file_text(file_name, package)


def try_get_file_text(file_name, package='sahara', **kwargs):
    return files.try_get_file_text(file_name, package)


def get_by_id(lst, id, **kwargs):
    return general.get_by_id(lst, id)


def natural_sort_key(s, **kwargs):
    return general.natural_sort_key(s)


def get_flavor(**kwargs):
    return nova.get_flavor(**kwargs)


def poll(get_status, kwargs=None, args=None, operation_name=None,
         timeout_name=None, timeout=poll_utils.DEFAULT_TIMEOUT,
         sleep=poll_utils.DEFAULT_SLEEP_TIME, exception_strategy='raise'):
    poll_utils.poll(get_status, kwargs=kwargs, args=args,
                    operation_name=operation_name,
                    timeout_name=timeout_name, timeout=timeout,
                    sleep=sleep, exception_strategy=exception_strategy)


def plugin_option_poll(cluster, get_status, option, operation_name,
                       sleep_time, kwargs):
    poll_utils.plugin_option_poll(cluster, get_status, option,
                                  operation_name, sleep_time, kwargs)


def create_proxy_user_for_cluster(cluster, **kwargs):
    return proxy.create_proxy_user_for_cluster(cluster)


def get_remote(instance, **kwargs):
    return remote.get_remote(instance)


def rpc_setup(service_name, **kwargs):
    rpc.setup(service_name)


def transform_to_num(s, **kwargs):
    return types.transform_to_num(s)


def is_int(s, **kwargs):
    return types.is_int(s)


def parse_hadoop_xml_with_name_and_value(data, **kwargs):
    return xmlutils.parse_hadoop_xml_with_name_and_value(data)


def create_hadoop_xml(configs, config_filter=None, **kwargs):
    return xmlutils.create_hadoop_xml(configs, config_filter)


def create_elements_xml(configs, **kwargs):
    return xmlutils.create_elements_xml(configs)


def load_hadoop_xml_defaults(file_name, package, **kwargs):
    return xmlutils.load_hadoop_xml_defaults(file_name, package)


def get_property_dict(elem, **kwargs):
    return xmlutils.get_property_dict(elem)


class PluginsApiValidator(api_validator.ApiValidator):
    def __init__(self, schema, **kwargs):
        super(PluginsApiValidator, self).__init__(schema)
