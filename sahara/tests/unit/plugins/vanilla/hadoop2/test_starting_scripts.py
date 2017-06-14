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

from sahara.plugins.vanilla.hadoop2 import starting_scripts as s_scripts
from sahara.tests.unit import base


class StartingScriptsTest(base.SaharaTestCase):

    plugins_path = 'sahara.plugins.vanilla.'

    def setUp(self):
        super(StartingScriptsTest, self).setUp()
        self.cluster = mock.Mock()

    @mock.patch(plugins_path + 'utils.get_namenode')
    @mock.patch(plugins_path + 'hadoop2.starting_scripts._start_namenode')
    def test_start_namenode(self, _start_namenode, get_namenode):
        namenode = mock.Mock()
        get_namenode.return_value = namenode
        s_scripts.start_namenode(self.cluster)
        get_namenode.assert_called_once_with(self.cluster)
        _start_namenode.assert_called_once_with(namenode)

    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch(plugins_path + 'hadoop2.run_scripts.start_hadoop_process')
    @mock.patch(plugins_path + 'hadoop2.run_scripts.format_namenode')
    def test__start_namenode(self, format_namenode,
                             start_hadoop_process,
                             check_cluster_exists):
        check_cluster_exists.return_value = None
        nn = mock.Mock()
        s_scripts._start_namenode(nn)
        format_namenode.assert_called_once_with(nn)
        start_hadoop_process.assert_called_once_with(nn, 'namenode')

    @mock.patch(plugins_path +
                'hadoop2.starting_scripts._start_secondarynamenode')
    @mock.patch(plugins_path + 'utils.get_secondarynamenode')
    def test_start_secondarynamenode(self, get_secondarynamenode,
                                     _start_secondarynamenode):
        get_secondarynamenode.return_value = 0
        s_scripts.start_secondarynamenode(self.cluster)
        get_secondarynamenode.assert_called_once_with(self.cluster)

        get_secondarynamenode.return_value = 1
        s_scripts.start_secondarynamenode(self.cluster)
        _start_secondarynamenode.assert_called_once_with(1)
        self.assertEqual(get_secondarynamenode.call_count, 2)

    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch(plugins_path + 'hadoop2.run_scripts.start_hadoop_process')
    def test__start_secondarynamenode(self, start_hadoop_process,
                                      check_cluster_exists):
        check_cluster_exists.return_value = None
        snn = mock.Mock()
        s_scripts._start_secondarynamenode(snn)
        start_hadoop_process.assert_called_once_with(snn,
                                                     'secondarynamenode')

    @mock.patch(plugins_path +
                'hadoop2.starting_scripts._start_resourcemanager')
    @mock.patch(plugins_path + 'utils.get_resourcemanager')
    def test_start_resourcemanager(self, get_resourcemanager,
                                   _start_resourcemanager):
        get_resourcemanager.return_value = 0
        s_scripts.start_resourcemanager(self.cluster)
        get_resourcemanager.assert_called_once_with(self.cluster)

        get_resourcemanager.return_value = 1
        s_scripts.start_resourcemanager(self.cluster)
        _start_resourcemanager.assert_called_once_with(1)
        self.assertEqual(get_resourcemanager.call_count, 2)

    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch(plugins_path + 'hadoop2.run_scripts.start_yarn_process')
    def test__start_resourcemanager(self, start_yarn_process,
                                    check_cluster_exists):
        check_cluster_exists.return_value = None
        snn = mock.Mock()
        s_scripts._start_resourcemanager(snn)
        start_yarn_process.assert_called_once_with(snn,
                                                   'resourcemanager')

    @mock.patch(plugins_path + 'hadoop2.run_scripts.start_historyserver')
    @mock.patch(plugins_path + 'utils.get_historyserver')
    def test_start_historyserver(self, get_historyserver,
                                 start_historyserver):
        get_historyserver.return_value = 0
        s_scripts.start_historyserver(self.cluster)
        get_historyserver.assert_called_once_with(self.cluster)

        get_historyserver.return_value = 1
        s_scripts.start_historyserver(self.cluster)
        start_historyserver.assert_called_once_with(1)
        self.assertEqual(get_historyserver.call_count, 2)

    @mock.patch(plugins_path + 'hadoop2.run_scripts.start_oozie_process')
    @mock.patch(plugins_path + 'utils.get_oozie')
    def test_start_oozie(self, get_oozie, start_oozie_process):
        pctx = mock.Mock()
        get_oozie.return_value = 0
        s_scripts.start_oozie(pctx, self.cluster)
        get_oozie.assert_called_once_with(self.cluster)

        get_oozie.return_value = 1
        s_scripts.start_oozie(pctx, self.cluster)
        start_oozie_process.assert_called_once_with(pctx, 1)
        self.assertEqual(get_oozie.call_count, 2)

    @mock.patch(plugins_path +
                'hadoop2.run_scripts.start_hiveserver_process')
    @mock.patch(plugins_path + 'utils.get_hiveserver')
    def test_start_hiveserver(self, get_hiveserver,
                              start_hiveserver_process):
        pctx = mock.Mock()
        get_hiveserver.return_value = 0
        s_scripts.start_hiveserver(pctx, self.cluster)
        get_hiveserver.assert_called_once_with(self.cluster)

        get_hiveserver.return_value = 1
        s_scripts.start_hiveserver(pctx, self.cluster)
        start_hiveserver_process.assert_called_once_with(pctx, 1)
        self.assertEqual(get_hiveserver.call_count, 2)

    @mock.patch(plugins_path +
                'hadoop2.run_scripts.start_spark_history_server')
    @mock.patch(plugins_path + 'utils.get_spark_history_server')
    def test_start_spark(self, get_spark_history_server,
                         start_spark_history_server):
        get_spark_history_server.return_value = 0
        s_scripts.start_spark(self.cluster)
        get_spark_history_server.assert_called_once_with(self.cluster)

        get_spark_history_server.return_value = 1
        s_scripts.start_spark(self.cluster)
        start_spark_history_server.assert_called_once_with(1)
        self.assertEqual(get_spark_history_server.call_count, 2)
