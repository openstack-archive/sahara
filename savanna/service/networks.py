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

import netaddr

from oslo.config import cfg

from savanna import conductor as c
from savanna import context
from savanna.utils.openstack import nova


conductor = c.API
CONF = cfg.CONF


# NOTE(slukjanov): https://blueprints.launchpad.net/savanna?searchtext=ip
def init_instances_ips(instance, server):
    if instance.internal_ip and instance.management_ip:
        return True

    if CONF.use_neutron:
        return init_neutron_ips(instance, server)
    else:
        return init_nova_network_ips(instance, server)


def init_neutron_ips(instance, server):
    ctx = context.ctx()

    net_id = instance.node_group.cluster.neutron_management_network
    net_name = nova.client().networks.get(net_id).label

    internal_ip = server.networks.get(net_name, [None])[0]
    management_ip = internal_ip

    conductor.instance_update(ctx, instance, {"management_ip": management_ip,
                                              "internal_ip": internal_ip})

    return internal_ip


def init_nova_network_ips(instance, server):
    """Extracts internal and management ips.

    As internal ip will be used the first ip from the nova networks CIDRs.
    If use_floating_ip flag is set than management ip will be the first
    non-internal ip.
    """
    ctx = context.ctx()

    management_ip = instance.management_ip
    internal_ip = instance.internal_ip

    for network_label in server.networks:
        nova_network = nova.client().networks.find(label=network_label)
        network = netaddr.IPNetwork(nova_network.cidr)
        for ip in server.networks[network_label]:
            if netaddr.IPAddress(ip) in network:
                internal_ip = instance.internal_ip or ip
            else:
                management_ip = instance.management_ip or ip

    if not CONF.use_floating_ips:
        management_ip = internal_ip

    conductor.instance_update(ctx, instance, {"management_ip": management_ip,
                                              "internal_ip": internal_ip})

    return internal_ip and management_ip
