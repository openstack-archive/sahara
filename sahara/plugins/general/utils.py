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

from six.moves.urllib import parse as urlparse

from sahara.openstack.common import network_utils
from sahara.plugins.general import exceptions as ex


def get_node_groups(cluster, node_process=None):
    return [ng for ng in cluster.node_groups
            if (node_process is None or
                node_process in [n.lower() for n in ng.node_processes])]


def get_instances_count(cluster, node_process=None):
    return sum([ng.count for ng in get_node_groups(cluster, node_process)])


def get_instances(cluster, node_process=None):
    nodes = get_node_groups(cluster, node_process)
    return reduce(lambda a, b: a + b.instances, nodes, [])


def get_instance(cluster, node_process):
    instances = get_instances(cluster, node_process)
    if len(instances) > 1:
        raise ex.InvalidComponentCountException(
            node_process, '0 or 1', len(instances))
    return instances[0] if instances else None


def get_namenode(cluster):
    return get_instance(cluster, "namenode")


#TODO(jmaron): name change?
def get_jobtracker(cluster):
    instance = get_instance(cluster, "jobtracker")
    if not instance:
        instance = get_resourcemanager(cluster)

    return instance


def get_resourcemanager(cluster):
    return get_instance(cluster, 'resourcemanager')


def get_nodemanagers(cluster):
    return get_instances(cluster, 'nodemanager')


def get_oozie(cluster):
    return get_instance(cluster, "oozie")


def get_hiveserver(cluster):
    return get_instance(cluster, "hiveserver")


def get_datanodes(cluster):
    return get_instances(cluster, 'datanode')


def get_tasktrackers(cluster):
    return get_instances(cluster, 'tasktracker')


def get_secondarynamenodes(cluster):
    return get_instances(cluster, 'secondarynamenode')


def get_historyserver(cluster):
    return get_instance(cluster, 'historyserver')


def generate_host_names(nodes):
    return "\n".join([n.hostname() for n in nodes])


def generate_fqdn_host_names(nodes):
    return "\n".join([n.fqdn() for n in nodes])


def get_port_from_address(address):
    parse_result = urlparse.urlparse(address)
    # urlparse do not parse values like 0.0.0.0:8000,
    # network_utils do not parse values like http://localhost:8000,
    # so combine approach is using
    if parse_result.port:
        return parse_result.port
    else:
        return network_utils.parse_host_port(address)[1]
