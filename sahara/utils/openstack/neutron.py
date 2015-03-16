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

import os
import shlex

from eventlet.green import subprocess as e_subprocess
from neutronclient.neutron import client as neutron_cli
import requests
from requests import adapters

from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.openstack.common import log as logging
from sahara.utils.openstack import base


LOG = logging.getLogger(__name__)


def client():
    ctx = context.ctx()
    args = {
        'username': ctx.username,
        'tenant_name': ctx.tenant_name,
        'tenant_id': ctx.tenant_id,
        'token': ctx.token,
        'endpoint_url': base.url_for(ctx.service_catalog, 'network')
    }
    return neutron_cli.Client('2.0', **args)


class NeutronClientRemoteWrapper():
    neutron = None
    adapters = {}
    routers = {}

    def __init__(self, network, uri, token, tenant_name):
        self.neutron = neutron_cli.Client('2.0',
                                          endpoint_url=uri,
                                          token=token,
                                          tenant_name=tenant_name)
        self.network = network

    def get_router(self):
        matching_router = NeutronClientRemoteWrapper.routers.get(self.network,
                                                                 None)
        if matching_router:
            LOG.debug('Returning cached qrouter')
            return matching_router['id']

        routers = self.neutron.list_routers()['routers']
        for router in routers:
            device_id = router['id']
            ports = self.neutron.list_ports(device_id=device_id)['ports']
            port = next((port for port in ports
                         if port['network_id'] == self.network), None)
            if port:
                matching_router = router
                NeutronClientRemoteWrapper.routers[
                    self.network] = matching_router
                break

        if not matching_router:
            raise ex.SystemError(_('Neutron router corresponding to network '
                                   '%s is not found') % self.network)

        return matching_router['id']

    def get_http_session(self, host, port=None, *args, **kwargs):
        session = requests.Session()
        adapters = self._get_adapters(host, port=port, *args, **kwargs)
        for adapter in adapters:
            session.mount('http://{0}:{1}'.format(host, adapter.port), adapter)

        return session

    def _get_adapters(self, host, port=None, *args, **kwargs):
        LOG.debug('Retrieving neutron adapters for {0}:{1}'.format(host, port))
        adapters = []
        if not port:
            # returning all registered adapters for given host
            adapters = [adapter for adapter in self.adapters
                        if adapter.host == host]
        else:
            # need to retrieve or create specific adapter
            adapter = self.adapters.get((host, port), None)
            if not adapter:
                LOG.debug('Creating neutron adapter for {0}:{1}'
                          .format(host, port))
                qrouter = self.get_router()
                adapter = (
                    NeutronHttpAdapter(qrouter, host, port, *args, **kwargs))
                self.adapters[(host, port)] = adapter
                adapters = [adapter]

        return adapters


class NeutronHttpAdapter(adapters.HTTPAdapter):
    port = None
    host = None

    def __init__(self, qrouter, host, port, *args, **kwargs):
        super(NeutronHttpAdapter, self).__init__(*args, **kwargs)
        command = 'ip netns exec qrouter-{0} nc {1} {2}'.format(qrouter,
                                                                host, port)
        LOG.debug('Neutron adapter created with cmd {0}'.format(command))
        self.cmd = shlex.split(command)
        self.port = port
        self.host = host

    def get_connection(self, url, proxies=None):
        pool_conn = (
            super(NeutronHttpAdapter, self).get_connection(url, proxies))
        if hasattr(pool_conn, '_get_conn'):
            http_conn = pool_conn._get_conn()
            if http_conn.sock is None:
                if hasattr(http_conn, 'connect'):
                    sock = self._connect()
                    LOG.debug('HTTP connection {0} getting new '
                              'netcat socket {1}'.format(http_conn, sock))
                    http_conn.sock = sock
            else:
                if hasattr(http_conn.sock, 'is_netcat_socket'):
                    LOG.debug('pooled http connection has existing '
                              'netcat socket. resetting pipe...')
                    http_conn.sock.reset()

            pool_conn._put_conn(http_conn)

        return pool_conn

    def close(self):
        LOG.debug('Closing neutron adapter for {0}:{1}'
                  .format(self.host, self.port))
        super(NeutronHttpAdapter, self).close()

    def _connect(self):
        LOG.debug('returning netcat socket with command {0}'
                  .format(self.cmd))
        return NetcatSocket(self.cmd)


class NetcatSocket:

    def _create_process(self):
        self.process = e_subprocess.Popen(self.cmd,
                                          stdin=e_subprocess.PIPE,
                                          stdout=e_subprocess.PIPE,
                                          stderr=e_subprocess.PIPE)

    def __init__(self, cmd):
        self.cmd = cmd
        self._create_process()

    def send(self, content):
        try:
            self.process.stdin.write(content)
            self.process.stdin.flush()
        except IOError as e:
            raise ex.SystemError(e)
        return len(content)

    def sendall(self, content):
        return self.send(content)

    def makefile(self, mode, *arg):
        if mode.startswith('r'):
            return self.process.stdout
        if mode.startswith('w'):
            return self.process.stdin
        raise ex.IncorrectStateError(_("Unknown file mode %s") % mode)

    def recv(self, size):
        try:
            return os.read(self.process.stdout.fileno(), size)
        except IOError as e:
            raise ex.SystemError(e)

    def _terminate(self):
        self.process.terminate()

    def close(self):
        LOG.debug('Socket close called')
        self._terminate()

    def settimeout(self, timeout):
        pass

    def fileno(self):
        return self.process.stdin.fileno()

    def is_netcat_socket(self):
        return True

    def reset(self):
        self._terminate()
        self._create_process()


def get_private_network_cidrs(cluster):
    neutron_client = client()
    private_net = neutron_client.show_network(
        cluster.neutron_management_network)

    cidrs = []
    for subnet_id in private_net['network']['subnets']:
        subnet = neutron_client.show_subnet(subnet_id)
        cidrs.append(subnet['subnet']['cidr'])

    return cidrs
