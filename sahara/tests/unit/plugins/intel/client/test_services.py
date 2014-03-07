# Copyright (c) 2014 Intel Corporation
# Copyright (c) 2014 Mirantis Inc.
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

from sahara.plugins.intel.client import services
from sahara.plugins.intel import exceptions as iex
from sahara.tests.unit import base


class HDFSServiceTest(base.SaharaTestCase):
    def test_get_datanode_status_nodomains(self):
        self.override_config("node_domain", "domain")
        ctx = mock.Mock()
        ctx.cluster_name = 'cluster'
        ctx.rest.get.return_value = {
            "items": [
                {"status": "Stopped", "hostname": "manager-001"},
                {"status": "Stopped", "hostname": "master-001"},
                {"status": "Running", "hostname": "worker-001"},
                {"status": "Running", "hostname": "worker-002"},
                {"status": "Decomissioned", "hostname": "worker-003"}]}

        hdfs = services.HDFSService(ctx, 'hdfs')
        self.assertEqual('Stopped',
                         hdfs.get_datanode_status('master-001.domain'))
        self.assertEqual('Running',
                         hdfs.get_datanode_status('worker-001.domain'))
        self.assertEqual('Decomissioned',
                         hdfs.get_datanode_status('worker-003.domain'))
        self.assertRaises(iex.IntelPluginException,
                          hdfs.get_datanode_status, 'worker-004.domain')

    def test_get_datanode_status_domains(self):
        self.override_config("node_domain", "domain")
        ctx = mock.Mock()
        ctx.cluster_name = 'cluster'
        ctx.rest.get.return_value = {
            "items": [
                {"status": "Stopped", "hostname": "manager-001.domain"},
                {"status": "Stopped", "hostname": "master-001.domain"},
                {"status": "Running", "hostname": "worker-001.domain"},
                {"status": "Running", "hostname": "worker-002.domain"},
                {"status": "Decomissioned", "hostname": "worker-003.domain"}]}

        hdfs = services.HDFSService(ctx, 'hdfs')
        self.assertEqual('Stopped',
                         hdfs.get_datanode_status('master-001.domain'))
        self.assertEqual('Running',
                         hdfs.get_datanode_status('worker-001.domain'))
        self.assertEqual('Decomissioned',
                         hdfs.get_datanode_status('worker-003.domain'))
        self.assertRaises(iex.IntelPluginException,
                          hdfs.get_datanode_status, 'worker-004.domain')
