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
import six

from sahara import conductor as c
from sahara import context
from sahara.utils.openstack import base as b
from sahara.utils.openstack import nova

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

    # tmckay-fp okay
    # conf.use_floating_ips becomes
    # "use a floating ip for the management ip if one is defined"
    # assignment comes from nova conf setting, or from floating_ip_pool value

    # tmckay-fp log an extra warning here in the neutron
    # case that the node group has a floating ip pool but
    # we don't have a management ip yet ...
    cluster = instance.cluster
    if (not CONF.use_floating_ips or not management_ip or
            (cluster.has_proxy_gateway() and
             not instance.node_group.is_proxy_gateway)):
        management_ip = internal_ip

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
