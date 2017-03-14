# Copyright (c) 2017 EasyStack Inc.
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

from sahara.plugins.ambari import common
from sahara.tests.unit import base


class AmbariCommonTestCase(base.SaharaTestCase):
    def setUp(self):
        super(AmbariCommonTestCase, self).setUp()
        self.master_ng = mock.Mock()
        self.master_ng.node_processes = ['Ambari', 'HiveServer']

        self.worker_ng = mock.Mock()
        self.worker_ng.node_processes = ['DataNode', 'Oozie']

        self.cluster = mock.Mock()
        self.cluster.node_groups = [self.master_ng, self.worker_ng]

    def test_get_ambari_proc_list(self):
        procs = common.get_ambari_proc_list(self.master_ng)
        expected = ['METRICS_COLLECTOR', 'HIVE_SERVER',
                    'MYSQL_SERVER', 'WEBHCAT_SERVER']
        self.assertEqual(procs, expected)

        procs = common.get_ambari_proc_list(self.worker_ng)
        expected = ['DATANODE', 'OOZIE_SERVER', 'PIG']
        self.assertEqual(procs, expected)

    @mock.patch('sahara.plugins.kerberos.is_kerberos_security_enabled')
    def test_get_clients(self, kerberos):
        kerberos.return_value = False
        clients = common.get_clients(self.cluster)
        expected = ['OOZIE_CLIENT', 'HIVE_CLIENT', 'HDFS_CLIENT',
                    'TEZ_CLIENT', 'METRICS_MONITOR']
        for e in expected:
            self.assertIn(e, clients)

        kerberos.return_value = True
        clients = common.get_clients(self.cluster)
        expected = ['OOZIE_CLIENT', 'HIVE_CLIENT', 'HDFS_CLIENT',
                    'TEZ_CLIENT', 'METRICS_MONITOR', 'KERBEROS_CLIENT']
        for e in expected:
            self.assertIn(e, clients)

    def test_instances_have_process(self):
        instance1 = mock.Mock()
        instance2 = mock.Mock()
        instance1.node_group = self.master_ng
        instance2.node_group = self.worker_ng
        self.assertTrue(common.instances_have_process([instance1], "Ambari"))
        self.assertTrue(common.instances_have_process([instance1, instance2],
                                                      "DataNode"))
        self.assertFalse(common.instances_have_process([instance1, instance2],
                                                       "DRPC Server"))
