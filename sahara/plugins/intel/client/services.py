# Copyright (c) 2013 Intel Corporation
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

from sahara import context
from sahara.openstack.common import log as logging
from sahara.plugins.intel.client import context as c
from sahara.plugins.intel.client import session
from sahara.plugins.intel import exceptions as iex


LOG = logging.getLogger(__name__)


class BaseService(c.IntelContext):
    def __init__(self, ctx, service_name):
        super(BaseService, self).__init__(ctx)
        self.service = service_name

    def start(self):
        url = ('/cluster/%s/services/%s/commands/start'
               % (self.cluster_name, self.service))

        self.rest.post(url)

        #TODO(alazarev) make timeout configurable (bug #1262897)
        timeout = 600
        cur_time = 0
        while cur_time < timeout:
            context.sleep(2)
            if self.status() == 'running':
                break
            else:
                cur_time += 2
        else:
            raise iex.IntelPluginException(
                "Service '%s' has failed to start in %s seconds"
                % (self.service, timeout))

    def stop(self):
        url = ('/cluster/%s/services/%s/commands/stop'
               % (self.cluster_name, self.service))

        return self.rest.post(url)

    def status(self):
        url = '/cluster/%s/services' % self.cluster_name
        statuses = self.rest.get(url)['items']
        for st in statuses:
            if st['serviceName'] == self.service:
                return st['status']

        raise iex.IntelPluginException(
            "Service '%s' is not installed on cluster '%s'"
            % (self.service, self.cluster_name))

    def get_nodes(self):
        url = '/cluster/%s/services/%s' % (self.cluster_name, self.service)
        return self.rest.get(url)

    def add_nodes(self, role, nodes):
        url = ('/cluster/%s/services/%s/roles'
               % (self.cluster_name, self.service))

        data = map(lambda host: {
            'rolename': role,
            'hostname': host
        }, nodes)

        return self.rest.post(url, data)


class HDFSService(BaseService):
    def format(self, force=False):
        url = ('/cluster/%s/services/hdfs/commands/hdfsformat/%s'
               % (self.cluster_name, 'force' if force else 'noforce'))

        session_id = self.rest.post(url)['sessionID']
        return session.wait(self, session_id)

    def decommission_nodes(self, nodes, force=False):
        url = ('/cluster/%s/nodes/commands/decommissionnodes/%s'
               % (self.cluster_name, 'force' if force else 'noforce'))
        data = map(lambda host: {
            'hostname': host
        }, nodes)

        return self.rest.post(url, data)

    def get_datanodes_status(self):
        url = '/cluster/%s/nodes/commands/datanodes/status' % self.cluster_name
        return self.rest.get(url)['items']

    def get_datanode_status(self, datanode):
        stats = self.get_datanodes_status()
        for stat in stats:
            hostname = stat['hostname']
            fqdn = hostname + '.' + cfg.CONF.node_domain
            if hostname == datanode or fqdn == datanode:
                return stat['status'].strip()

        raise iex.IntelPluginException(
            "Datanode service is is not installed on node '%s'" % datanode)


class Services(c.IntelContext):
    def __init__(self, ctx, is_yarn_supported):
        super(Services, self).__init__(ctx)
        self.hdfs = HDFSService(self, 'hdfs')
        if is_yarn_supported:
            self.yarn = BaseService(self, 'yarn')
        else:
            self.mapred = BaseService(self, 'mapred')
        self.hive = BaseService(self, 'hive')
        self.oozie = BaseService(self, 'oozie')

    def add(self, services):
        _services = map(lambda service: {
            'serviceName': service,
            'type': service
        }, services)
        url = '/cluster/%s/services' % self.cluster_name

        return self.rest.post(url, _services)

    def get_services(self):
        url = '/cluster/%s/services' % self.cluster_name

        return self.rest.get(url)

    def delete_service(self, service):
        url = '/cluster/%s/services/%s' % (self.cluster_name, service)
        return self.rest.delete(url)
