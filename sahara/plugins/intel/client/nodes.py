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

from sahara.plugins.intel.client import context as c
from sahara.plugins.intel.client import session
from sahara.plugins.intel import exceptions as iex


class Nodes(c.IntelContext):
    def add(self, nodes, rack, username, path_to_key, keypass=''):
        hosts = {
            'method': 'useauthzkeyfile',
            'nodeinfo': map(lambda host: {
                'hostname': host,
                'username': username,
                'passphrase': keypass,
                'authzkeyfile': path_to_key,
                'rackName': rack
            }, nodes)
        }

        url = '/cluster/%s/nodes' % self.cluster_name
        resp = self.rest.post(url, hosts)['items']

        for node_info in resp:
            if node_info['info'] != 'Connected':
                raise iex.IntelPluginException(
                    'Error adding nodes: %s' % node_info['iporhostname'])

    def get(self):
        url = '/cluster/%s/nodes' % self.cluster_name
        return self.rest.get(url)

    def get_status(self, node):
        url = '/cluster/%s/nodes/%s' % (self.cluster_name, node)
        return self.rest.get(url)['status']

    def delete(self, node):
        url = '/cluster/%s/nodes/%s' % (self.cluster_name, node)
        return self.rest.delete(url)

    def config(self, force=False):
        url = ('/cluster/%s/nodes/commands/confignodes/%s'
               % (self.cluster_name, 'force' if force else 'noforce'))

        session_id = self.rest.post(url)['sessionID']
        return session.wait(self, session_id)

    def stop(self, nodes):
        url = '/cluster/%s/nodes/commands/stopnodes' % self.cluster_name
        data = [{'hostname': host} for host in nodes]

        return self.rest.post(url, data)
