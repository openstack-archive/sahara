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

from savanna import conductor as c
from savanna import context
from savanna.utils.openstack import nova


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
        if CONF.use_neutron:
            nova.client().floating_ips.delete(fl_ip.id)
        else:
            nova.client().floating_ips.delete(fl_ip.ip)
