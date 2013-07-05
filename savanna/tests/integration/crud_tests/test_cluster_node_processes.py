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

import telnetlib

from savanna.tests.integration import base


class ClusterNodeProcessesCrudTest(base.ITestCase):

    def setUp(self):
        super(ClusterNodeProcessesCrudTest, self).setUp()

        telnetlib.Telnet(self.host, self.port)

    def test_crud_cluster_nn(self):
        """This test checks cluster creation with topology | NN | via
        node process.
        """
        node_processes = {'NN': 1}
        body = self.make_cl_body_node_processes(node_processes)
        self.crud_object(body, self.url_cluster)

    def test_crud_cluster_nn_dn(self):
        """This test checks cluster creation with topology | NN | DN | via
        node processes.
        """
        node_processes = {'NN': 1, 'DN': 2}
        body = self.make_cl_body_node_processes(node_processes)
        self.crud_object(body, self.url_cluster)
