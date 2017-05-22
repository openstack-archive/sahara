# Copyright (c) 2013 Hortonworks, Inc.
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


from neutronclient.common import exceptions as n_ex
from neutronclient.neutron import client as neutron_cli
from oslo_config import cfg
from oslo_log import log as logging

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service import sessions
from sahara.utils.openstack import base
from sahara.utils.openstack import keystone


opts = [
    cfg.BoolOpt('api_insecure',
                default=False,
                help='Allow to perform insecure SSL requests to neutron.'),
    cfg.StrOpt('ca_file',
               help='Location of ca certificates file to use for neutron '
                    'client requests.'),
    cfg.StrOpt("endpoint_type",
               default="internalURL",
               help="Endpoint type for neutron client requests")
]

neutron_group = cfg.OptGroup(name='neutron',
                             title='Neutron client options')

CONF = cfg.CONF
CONF.register_group(neutron_group)
CONF.register_opts(opts, group=neutron_group)

LOG = logging.getLogger(__name__)


def client(auth=None):
    if not auth:
        auth = keystone.auth()
    session = sessions.cache().get_session(sessions.SESSION_TYPE_NEUTRON)
    neutron = neutron_cli.Client('2.0', session=session, auth=auth,
                                 endpoint_type=CONF.neutron.endpoint_type,
                                 region_name=CONF.os_region_name)
    return neutron


class NeutronClient(object):
    neutron = None
    routers = {}

    def __init__(self, network, token, tenant_name, auth=None):
        if not auth:
            auth = keystone.token_auth(token=token, project_name=tenant_name)
        self.neutron = client(auth)
        self.network = network

    def get_router(self):
        matching_router = NeutronClient.routers.get(self.network, None)
        if matching_router:
            LOG.debug('Returning cached qrouter')
            return matching_router['id']

        routers = self.neutron.list_routers()['routers']
        for router in routers:
            device_id = router['id']
            ports = base.execute_with_retries(
                self.neutron.list_ports, device_id=device_id)['ports']
            port = next((port for port in ports
                         if port['network_id'] == self.network), None)
            if port:
                matching_router = router
                NeutronClient.routers[self.network] = matching_router
                break

        if not matching_router:
            raise ex.SystemError(_('Neutron router corresponding to network '
                                   '%s is not found') % self.network)

        return matching_router['id']


def get_private_network_cidrs(cluster):
    neutron_client = client()
    private_net = base.execute_with_retries(neutron_client.show_network,
                                            cluster.neutron_management_network)

    cidrs = []
    for subnet_id in private_net['network']['subnets']:
        subnet = base.execute_with_retries(
            neutron_client.show_subnet, subnet_id)
        cidrs.append(subnet['subnet']['cidr'])

    return cidrs


def get_network(id):
    try:
        return base.execute_with_retries(
            client().find_resource_by_id, 'network', id)
    except n_ex.NotFound:
        return None
