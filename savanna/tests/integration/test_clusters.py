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

import copy
from savanna.tests.integration.db import ValidationTestCase
from telnetlib import Telnet


class TestValidationApiForClusters(ValidationTestCase):

    def setUp(self):
        super(TestValidationApiForClusters, self).setUp()
        Telnet(self.host, self.port)

    def test_crud_operation_for_cluster(self):
        get_body = copy.deepcopy(self.get_cluster_data_jtnn_ttdn)
        self._crud_object(
            self.cluster_data_jtnn_ttdn, get_body, self.url_cluster)

    def test_crud_operation_for_cluster_with_one_node(self):
        get_body = copy.deepcopy(self.get_cluster_data_jtnn)
        self._crud_object(self.cluster_data_jtnn, get_body, self.url_cluster)
