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


class Cluster(c.IntelContext):
    def create(self):
        url = '/cluster'
        data = {
            'name': self.cluster_name,
            'dnsresolution': True,
            'acceptlicense': True
        }

        return self.rest.post(url, data)

    def get(self):
        url = '/cluster/%s' % self.cluster_name
        return self.rest.get(url)

    def install_software(self, nodes):
        _nodes = [{'hostname': host} for host in nodes]
        url = '/cluster/%s/nodes/commands/installsoftware' % self.cluster_name
        session_id = self.rest.post(url, _nodes)['sessionID']
        return session.wait(self, session_id)

    def upload_authzkeyfile(self, authzkeyfile):
        url = '/cluster/%s/upload/authzkey' % self.cluster_name
        return self.rest.post(url,
                              files={'file': authzkeyfile})['upload result']
