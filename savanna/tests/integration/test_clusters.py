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

from savanna.tests.integration.db import ITestCase
import savanna.tests.integration.parameters as param
from telnetlib import Telnet


class ITestClusterApi(ITestCase):

    def setUp(self):
        super(ITestClusterApi, self).setUp()
        Telnet(self.host, self.port)

    def test_cluster_crud_operations(self):
        nt_body = self.make_nt('master-node', 'JT+NN', 1234, 2345)
        data_nt_master = self._post_object(self.url_nt, nt_body, 202)

        nt_body = self.make_nt('worker-node', 'TT+DN', 1234, 2345)
        data_nt_worker = self._post_object(self.url_nt, nt_body, 202)

        try:
            cluster_body = self.make_cluster_body(
                param.CLUSTER_NAME_CRUD, 'master-node',
                'worker-node', 2)
            get_cluster_body = self._get_body_cluster(
                param.CLUSTER_NAME_CRUD, 'master-node',
                'worker-node', 2)

            self._crud_object(cluster_body, get_cluster_body, self.url_cluster)

        finally:
            self.delete_node_template(data_nt_master)
            self.delete_node_template(data_nt_worker)
