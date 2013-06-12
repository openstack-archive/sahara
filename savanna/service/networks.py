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

from savanna.utils.openstack import nova

CONF = cfg.CONF

cluster_node_opts = [
    cfg.BoolOpt('use_floating_ips',
                default=True,
                help='When set to false, Savanna uses only internal IP of VMs.'
                     ' When set to true, Savanna expects OpenStack to auto-'
                     'assign floating IPs to cluster nodes. Internal IPs will '
                     'be used for inter-cluster communication, while floating '
                     'ones will be used by Savanna to configure nodes. Also '
                     'floating IPs will be exposed in service URLs.')
]

CONF.register_opts(cluster_node_opts)


# NOTE(slukjanov): https://blueprints.launchpad.net/savanna?searchtext=ip
def init_instances_ips(instance, server):
    """Extracts internal and management ips.

    As internal ip will be used the first ip from the nova networks CIDRs.
    If use_floating_ip flag is set than management ip will be the first
    non-internal ip.
    """
    if instance.internal_ip and instance.management_ip:
        return True

    for network_label in server.networks:
        nova_network = nova.client().networks.find(label=network_label)
        network = netaddr.IPNetwork(nova_network.cidr)
        for ip in server.networks[network_label]:
            if netaddr.IPAddress(ip) in network:
                instance.internal_ip = instance.internal_ip or ip
            else:
                instance.management_ip = instance.management_ip or ip

    if not CONF.use_floating_ips:
        instance.management_ip = instance.internal_ip

    return instance.internal_ip and instance.management_ip
