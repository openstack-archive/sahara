# Copyright (c) 2015 Mirantis Inc.
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


import mock

from sahara.plugins.ambari import common as p_common
from sahara.plugins.ambari import plugin
from sahara.tests.unit import base


class GetPortsTestCase(base.SaharaTestCase):
    def setUp(self):
        super(GetPortsTestCase, self).setUp()
        self.plugin = plugin.AmbariPluginProvider()

    def test_get_ambari_port(self):
        ng = mock.Mock()
        ng.node_processes = [p_common.AMBARI_SERVER]
        ports = self.plugin.get_open_ports(ng)
        self.assertEqual([8080], ports)
