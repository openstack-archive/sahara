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

from sahara.plugins.vanilla.hadoop2 import utils as u
from sahara.tests.unit import base
from sahara.utils import files


class UtilsTestCase(base.SaharaTestCase):
    @mock.patch('sahara.plugins.vanilla.utils.get_namenode')
    def test_datanodes_status(self, nn):
        report = files.get_file_text(
            'tests/unit/plugins/vanilla/hadoop2/resources/dfs-report.txt')

        nn.return_value = self._get_instance(report)
        statuses = u.get_datanodes_status(None)

        expected = {
            'cluster-worker-001.novalocal': 'normal',
            'cluster-worker-002.novalocal': 'normal',
            'cluster-worker-003.novalocal': 'normal',
            'cluster-worker-004.novalocal': 'decommissioned'
        }

        self.assertEqual(expected, statuses)

    @mock.patch('sahara.plugins.vanilla.utils.get_resourcemanager')
    def test_nodemanagers_status(self, rm):
        report = files.get_file_text(
            'tests/unit/plugins/vanilla/hadoop2/resources/yarn-report.txt')

        rm.return_value = self._get_instance(report)
        statuses = u.get_nodemanagers_status(None)

        expected = {
            'cluster-worker-001.novalocal': 'running',
            'cluster-worker-002.novalocal': 'running',
            'cluster-worker-003.novalocal': 'running',
            'cluster-worker-004.novalocal': 'decommissioned'
        }

        self.assertEqual(expected, statuses)

    def _get_instance(self, out):
        inst_remote = mock.MagicMock()
        inst_remote.execute_command.return_value = 0, out
        inst_remote.__enter__.return_value = inst_remote

        inst = mock.MagicMock()
        inst.remote.return_value = inst_remote

        return inst
