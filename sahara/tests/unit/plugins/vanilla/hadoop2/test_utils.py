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

    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.service.castellan.utils.get_secret')
    @mock.patch('sahara.service.castellan.utils.store_secret')
    @mock.patch('sahara.plugins.vanilla.utils')
    @mock.patch('sahara.conductor.API.cluster_update')
    def test_oozie_password(self, cluster_update, vu,
                            store_secret, get_secret, conductor):
        cluster = mock.MagicMock()
        cluster.extra = mock.MagicMock()
        cluster.extra.to_dict.return_value = {"oozie_pass_id": "31415926"}

        conductor.return_value = cluster

        get_secret.return_value = "oozie_pass"
        result = u.get_oozie_password(cluster)

        get_secret.assert_called_once_with("31415926")
        vu.generate_random_password.assert_not_called()
        self.assertEqual('oozie_pass', result)

        cluster.extra.to_dict.return_value = {}

        store_secret.return_value = 'oozie_pass'
        result = u.get_oozie_password(cluster)
        self.assertEqual('oozie_pass', result)

    @mock.patch('sahara.service.castellan.utils.delete_secret')
    def test_delete_oozie_password(self, delete_secret):
        cluster = mock.MagicMock()
        cluster.extra.to_dict = mock.MagicMock()

        cluster.extra.to_dict.return_value = {}
        u.delete_oozie_password(cluster)
        delete_secret.assert_not_called()

        cluster.extra.to_dict.return_value = {"oozie_pass_id": "31415926"}
        u.delete_oozie_password(cluster)
        delete_secret.assert_called_once_with("31415926")

    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.service.castellan.utils.get_secret')
    @mock.patch('sahara.service.castellan.utils.store_secret')
    @mock.patch('sahara.conductor.API.cluster_update')
    def test_get_hive_password(self, cluster_update,
                               store_secret, get_secret, conductor):
        cluster = mock.MagicMock()
        cluster.extra.to_dict.return_value = {"hive_pass_id": "31415926"}

        conductor.return_value = cluster

        get_secret.return_value = "hive_pass"
        result = u.get_hive_password(cluster)

        get_secret.assert_called_once_with("31415926")
        self.assertEqual('hive_pass', result)

        cluster.extra.to_dict.return_value = {}

        store_secret.return_value = 'hive_pass'
        result = u.get_hive_password(cluster)
        self.assertEqual('hive_pass', result)

    @mock.patch('sahara.service.castellan.utils.delete_secret')
    def test_delete_hive_password(self, delete_secret):
        cluster = mock.MagicMock()

        cluster.extra.to_dict.return_value = {}
        u.delete_hive_password(cluster)
        delete_secret.assert_not_called()

        cluster.extra.to_dict.return_value = {"hive_pass_id": "31415926"}

        u.delete_hive_password(cluster)
        delete_secret.assert_called_once_with("31415926")
