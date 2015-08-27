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

from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara import conductor as c
from sahara import context
from sahara.utils.openstack import base as b
from sahara.utils.openstack import neutron
from sahara.utils.openstack import nova

LOG = logging.getLogger(__name__)

conductor = c.API
CONF = cfg.CONF


def init_instances_ips(instance):
    """Extracts internal and management ips.

    As internal ip will be used the first ip from the nova networks CIDRs.
    If use_floating_ip flag is set than management ip will be the first
    non-internal ip.
    """

    server = nova.get_instance_info(instance)

    management_ip = None
    internal_ip = None

    for addresses in six.itervalues(server.addresses):
        # selects IPv4 preferentially
        for address in sorted(addresses, key=lambda addr: addr['version']):
            if address['OS-EXT-IPS:type'] == 'fixed':
                internal_ip = internal_ip or address['addr']
            else:
                management_ip = management_ip or address['addr']

    cluster = instance.cluster
    if (not CONF.use_floating_ips or
            (cluster.has_proxy_gateway() and
             not instance.node_group.is_proxy_gateway)):
        management_ip = internal_ip

    # NOTE(aignatov): Once bug #1262529 is fixed this 'if' block should be
    # reviewed and reformatted again, probably removed completely.
    if CONF.use_neutron and not (management_ip and internal_ip):
        LOG.debug("Instance doesn't yet contain Floating IP or Internal IP. "
                  "Floating IP={mgmt_ip}, Internal IP={internal_ip}. "
                  "Trying to get via Neutron.".format(
                      mgmt_ip=management_ip, internal_ip=internal_ip))
        neutron_client = neutron.client()
        ports = b.execute_with_retries(
            neutron_client.list_ports, device_id=server.id)["ports"]
        if ports:
            target_port_id = ports[0]['id']
            fl_ips = b.execute_with_retries(
                neutron_client.list_floatingips,
                port_id=target_port_id)['floatingips']
            if fl_ips:
                fl_ip = fl_ips[0]
                if not internal_ip:
                    internal_ip = fl_ip['fixed_ip_address']
                    LOG.debug('Found fixed IP {internal_ip}'
                              .format(internal_ip=internal_ip))
                # Zeroing management_ip if Sahara in private network
                if not CONF.use_floating_ips:
                    management_ip = internal_ip
                elif not management_ip:
                    management_ip = fl_ip['floating_ip_address']
                    LOG.debug('Found floating IP {mgmt_ip}'
                              .format(mgmt_ip=management_ip))

    conductor.instance_update(context.ctx(), instance,
                              {"management_ip": management_ip,
                               "internal_ip": internal_ip})

    return internal_ip and management_ip


def assign_floating_ip(instance_id, pool):
    ip = b.execute_with_retries(nova.client().floating_ips.create, pool)
    server = b.execute_with_retries(nova.client().servers.get, instance_id)
    b.execute_with_retries(server.add_floating_ip, ip)


def delete_floating_ip(instance_id):
    fl_ips = b.execute_with_retries(
        nova.client().floating_ips.findall, instance_id=instance_id)
    for fl_ip in fl_ips:
        b.execute_with_retries(nova.client().floating_ips.delete, fl_ip.id)
