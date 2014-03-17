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

from sahara.plugins.intel.client import cluster
from sahara.plugins.intel.client import nodes
from sahara.plugins.intel.client import params
from sahara.plugins.intel.client import rest as r
from sahara.plugins.intel.client import services


class IntelClient():
    def __init__(self, manager, cluster_name):
        #TODO(alazarev) make credentials configurable (bug #1262881)
        self.rest = r.RESTClient(manager, 'admin', 'admin', 'v1')
        self.cluster_name = cluster_name
        self._ctx = self

        self.cluster = cluster.Cluster(self)
        self.nodes = nodes.Nodes(self)
        self.params = params.Params(self, False)
        self.services = services.Services(self, False)
