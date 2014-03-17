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

from oslo.config import cfg
import six

from sahara import conductor as c
from sahara import context
from sahara.openstack.common import log as logging
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

    for network_label, addresses in six.iteritems(server.addresses):
        for address in addresses:
            if address['OS-EXT-IPS:type'] == 'fixed':
                internal_ip = internal_ip or address['addr']
            else:
                management_ip = management_ip or address['addr']

    if not CONF.use_floating_ips:
        management_ip = internal_ip

    if not management_ip and CONF.use_neutron:
        neutron_client = neutron.client()
        target_port = None
        for port in neutron_client.list_ports()["ports"]:
            if port["device_id"] == server.id:
                target_port = port
                break

        for fl_ip in neutron_client.list_floatingips()['floatingips']:
            if fl_ip['port_id'] == target_port['id']:
                management_ip = fl_ip['floating_ip_address']
                LOG.debug('Found floating IP %s for %s' % (management_ip,
                                                           server.name))
                break

    conductor.instance_update(context.ctx(), instance,
                              {"management_ip": management_ip,
                               "internal_ip": internal_ip})

    return internal_ip and management_ip


def assign_floating_ip(instance_id, pool):
    ip = nova.client().floating_ips.create(pool)
    nova.client().servers.get(instance_id).add_floating_ip(ip)


def delete_floating_ip(instance_id):
    fl_ips = nova.client().floating_ips.findall(instance_id=instance_id)
    for fl_ip in fl_ips:
        nova.client().floating_ips.delete(fl_ip.id)
