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

from unittest import mock

from sahara.plugins import exceptions as ex
from sahara.service.edp import hdfs_helper as helper
from sahara.tests.unit import base


class HDFSHelperTestCase(base.SaharaTestCase):
    def setUp(self):
        super(HDFSHelperTestCase, self).setUp()

        self.cluster = mock.MagicMock()
        self.cluster.id = '1axx'

    def test_create_hbase_common_lib_no_ex(self):

        def _command(a):
            if a == 'hbase classpath':
                return [0, 'april:may.jar:june']

        self.cluster.execute_command.side_effect = _command

        helper.create_hbase_common_lib(self.cluster)
        calls = [
            mock.call(('sudo su - -c "hdfs dfs -mkdir -p '
                       '/user/sahara-hbase-lib" hdfs')),
            mock.call('hbase classpath'),
            mock.call(('sudo su - -c "hdfs dfs -put -p may.jar '
                      '/user/sahara-hbase-lib" hdfs'))]
        self.cluster.execute_command.assert_has_calls(calls)

    def test_create_hbase_common_lib_ex(self):

        def _command(a):
            if a == 'hbase classpath':
                return [1, 'april:may.jar:june']

        self.cluster.execute_command.side_effect = _command

        self.assertRaises(ex.RequiredServiceMissingException,
                          helper.create_hbase_common_lib,
                          self.cluster)

    def test_copy_from_local(self):
        helper.copy_from_local(self.cluster, 'Galaxy', 'Earth', 'BigBang')
        self.cluster.execute_command.assert_called_once_with(
            'sudo su - -c "hdfs dfs -copyFromLocal Galaxy Earth" BigBang')

    def test_move_from_local(self):
        helper.move_from_local(self.cluster, 'Galaxy', 'Earth', 'BigBang')
        self.cluster.execute_command.assert_called_once_with(
            'sudo su - -c "hdfs dfs -copyFromLocal Galaxy Earth" BigBang '
            '&& sudo rm -f Galaxy')

    def test_create_dir_hadoop1(self):
        helper.create_dir_hadoop1(self.cluster, 'Earth', 'BigBang')
        self.cluster.execute_command.assert_called_once_with(
            'sudo su - -c "hdfs dfs -mkdir Earth" BigBang')

    def test_create_dir_hadoop2(self):
        helper.create_dir_hadoop2(self.cluster, 'Earth', 'BigBang')
        self.cluster.execute_command.assert_called_once_with(
            'sudo su - -c "hdfs dfs -mkdir -p Earth" BigBang')

    @mock.patch('sahara.utils.cluster.generate_etc_hosts')
    @mock.patch('sahara.plugins.utils.get_instances')
    @mock.patch('sahara.conductor.api.LocalApi.cluster_get_all')
    def test_get_cluster_hosts_information_smthg_wrong(self, mock_get_all,
                                                       mock_get_inst,
                                                       mock_generate):
        res = helper._get_cluster_hosts_information('host', self.cluster)
        self.assertIsNone(res)

    @mock.patch('sahara.context.ctx')
    @mock.patch('sahara.utils.cluster.generate_etc_hosts')
    @mock.patch('sahara.plugins.utils.get_instances')
    @mock.patch('sahara.conductor.api.LocalApi.cluster_get_all')
    def test_get_cluster_hosts_information_c_id(self, mock_get_all,
                                                mock_get_inst, mock_generate,
                                                mock_ctx):
        cluster = mock.MagicMock()
        cluster.id = '1axx'
        instance = mock.MagicMock()
        instance.instance_name = 'host'
        mock_get_all.return_value = [cluster]
        mock_get_inst.return_value = [instance]
        res = helper._get_cluster_hosts_information('host', self.cluster)
        self.assertIsNone(res)

    @mock.patch('sahara.context.ctx')
    @mock.patch('sahara.utils.cluster.generate_etc_hosts')
    @mock.patch('sahara.plugins.utils.get_instances')
    @mock.patch('sahara.conductor.api.LocalApi.cluster_get_all')
    def test_get_cluster_hosts_information_i_name(self, mock_get_all,
                                                  mock_get_inst, mock_generate,
                                                  mock_ctx):
        cluster = mock.MagicMock()
        cluster.id = '1axz'
        instance = mock.MagicMock()
        instance.instance_name = 'host'
        mock_get_all.return_value = [cluster]
        mock_get_inst.return_value = [instance]
        res = helper._get_cluster_hosts_information('host', self.cluster)
        self.assertEqual(res, mock_generate())

    @mock.patch('sahara.service.edp.hdfs_helper._is_cluster_configured')
    @mock.patch('six.text_type')
    @mock.patch('sahara.plugins.utils.get_instances')
    @mock.patch(('sahara.service.edp.hdfs_helper._get_cluster_hosts_'
                 'information'))
    def test_configure_cluster_for_hdfs(self, mock_helper, mock_get, mock_six,
                                        cluster_conf):
        cluster_conf.return_value = False
        inst = mock.MagicMock()
        inst.remote = mock.MagicMock()
        mock_six.return_value = 111
        str1 = '/tmp/etc-hosts-update.111'
        str2 = ('cat /tmp/etc-hosts-update.111 /etc/hosts | sort | uniq > '
                '/tmp/etc-hosts.111 && cat /tmp/etc-hosts.111 > '
                '/etc/hosts && rm -f /tmp/etc-hosts.111 '
                '/tmp/etc-hosts-update.111')
        mock_get.return_value = [inst]
        helper.configure_cluster_for_hdfs(self.cluster, "www.host.ru")
        inst.remote.assert_has_calls(
            [mock.call(), mock.call().__enter__(),
             mock.call().__enter__().write_file_to(str1, mock_helper()),
             mock.call().__enter__().execute_command(str2, run_as_root=True),
             mock.call().__exit__(None, None, None)])

    @mock.patch('sahara.plugins.utils.get_instances')
    def test_is_cluster_configured(self, mock_get):
        inst = mock.Mock()
        r = mock.MagicMock()
        inst.remote = mock.Mock(return_value=r)
        enter_r = mock.Mock()
        enter_r.execute_command = mock.Mock()
        enter_r.execute_command.return_value = 0, "127.0.0.1 localhost\n" + \
            "127.0.0.2 t1 t1"
        r.__enter__.return_value = enter_r

        cmd = 'cat /etc/hosts'
        host_info = ['127.0.0.1 localhost', '127.0.0.2 t1 t1']
        mock_get.return_value = [inst]
        res = helper._is_cluster_configured(self.cluster, host_info)
        self.assertTrue(res)
        enter_r.execute_command.assert_called_with(cmd)

        enter_r.execute_command.return_value = 0, "127.0.0.1 localhost\n"
        res = helper._is_cluster_configured(self.cluster, host_info)
        self.assertFalse(res)
        enter_r.execute_command.assert_called_with(cmd)

    @mock.patch('six.text_type')
    @mock.patch('os.open')
    def test_put_file_to_hdfs(self, open_get, mock_six):
        open_get.return_value = '/tmp/workflow.xml'
        mock_six.return_value = 111
        helper.put_file_to_hdfs(self.cluster, open_get, 'workflow',
                                '/tmp', 'hdfs')
        self.cluster.execute_command.assert_called_once_with(
            'sudo su - -c "hdfs dfs -copyFromLocal /tmp/workflow.111'
            ' /tmp/workflow" hdfs && sudo rm -f /tmp/workflow.111')
