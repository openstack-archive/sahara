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

from sahara.i18n import _
from sahara.plugins import utils as pu
from sahara.plugins.vanilla.hadoop2 import config_helper as c_helper
from sahara.plugins.vanilla.hadoop2 import run_scripts as rs
from sahara.tests.unit import base
from sahara.utils import edp
from sahara.utils import files


class RunScriptsTest(base.SaharaTestCase):

    PLUGINS_PATH = 'sahara.plugins.vanilla.hadoop2.'

    def setUp(self):
        super(RunScriptsTest, self).setUp()
        self.instance = mock.Mock()
        self.r = mock.Mock()
        self.remote = mock.Mock(return_value=self.r)
        self.remote.__enter__ = self.remote
        self.remote.__exit__ = mock.Mock()
        self.instance.remote.return_value = self.remote

    @mock.patch(PLUGINS_PATH + 'run_scripts._start_processes')
    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    @mock.patch('sahara.plugins.utils.instances_with_services')
    def test_start_dn_nm_processes(self, instances_with_services,
                                   add_provisioning_step,
                                   set_current_instance_id,
                                   _start_processes):
        ins = mock.Mock()
        ins.cluster_id = '111'
        ins.instance_id = '123'
        ins.instance_name = 'ins_1'
        instances = [ins]
        instances_with_services.return_value = instances
        mess = pu.start_process_event_message('DataNodes, NodeManagers')
        ins.node_group.node_processes = ['datanode', 'test']
        rs.start_dn_nm_processes(instances)
        instances_with_services.assert_called_once_with(
            instances, ['datanode', 'nodemanager'])
        add_provisioning_step.assert_called_once_with('111', mess, 1)
        set_current_instance_id.assert_called_once_with('123')
        _start_processes.assert_called_once_with(ins, ['datanode'])

    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    def test_start_processes_datanode(self, check_cluster_exists):
        processes = ['datanode']
        rs._start_processes(self.instance, processes)
        self.r.execute_command.assert_called_once_with(
            'sudo su - -c "hadoop-daemon.sh start datanode" hadoop')

    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    def test_start_processes_nodemanager(self, check_cluster_exists):
        processes = ['nodemanager']
        rs._start_processes(self.instance, processes)
        self.r.execute_command.assert_called_once_with(
            'sudo su - -c  "yarn-daemon.sh start nodemanager" hadoop')

    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    def test_start_processes_both(self, check_cluster_exists):
        processes = ['datanode', 'nodemanager']
        rs._start_processes(self.instance, processes)
        cmd_1 = 'sudo su - -c "hadoop-daemon.sh start datanode" hadoop'
        cmd_2 = 'sudo su - -c  "yarn-daemon.sh start nodemanager" hadoop'
        calls = [mock.call(cmd_1), mock.call(cmd_2)]
        self.r.execute_command.assert_has_calls(calls, any_order=True)

    def test_start_hadoop_process(self):
        process = 'test'
        rs.start_hadoop_process(self.instance, process)
        self.remote.execute_command.assert_called_once_with(
            'sudo su - -c "hadoop-daemon.sh start %s" hadoop' % process)

    def test_start_yarn_process(self):
        process = 'test'
        rs.start_yarn_process(self.instance, process)
        self.remote.execute_command.assert_called_once_with(
            'sudo su - -c  "yarn-daemon.sh start %s" hadoop' % process)

    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_start_historyserver(self, add_provisioning_step,
                                 check_cluster_exists):
        rs.start_historyserver(self.instance)
        self.remote.execute_command.assert_called_once_with(
            'sudo su - -c "mr-jobhistory-daemon.sh start historyserver" ' +
            'hadoop')

    @mock.patch(PLUGINS_PATH + 'run_scripts._start_oozie')
    @mock.patch(PLUGINS_PATH + 'run_scripts._oozie_share_lib')
    @mock.patch(PLUGINS_PATH + 'run_scripts._start_mysql')
    @mock.patch(PLUGINS_PATH + 'config_helper.is_mysql_enabled')
    @mock.patch(PLUGINS_PATH + 'utils.get_oozie_password')
    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_start_oozie_process(self, add_provisioning_step,
                                 check_cluster_exists,
                                 set_current_instance_id, get_oozie_password,
                                 is_mysql_enabled, _start_mysql,
                                 _oozie_share_lib, _start_oozie):
        self.instance.instance_id = '112233'
        pctx = mock.Mock()
        is_mysql_enabled.return_value = True
        sql_script = files.get_file_text(
            'plugins/vanilla/hadoop2/resources/create_oozie_db.sql')
        get_oozie_password.return_value = '123'
        pwd_script = sql_script.replace('password', '123')
        rs.start_oozie_process(pctx, self.instance)
        set_current_instance_id.assert_called_once_with('112233')
        is_mysql_enabled.assert_called_once_with(pctx,
                                                 self.instance.cluster)
        _start_mysql.assert_called_once_with(self.r)
        self.r.write_file_to.assert_called_once_with('create_oozie_db.sql',
                                                     pwd_script)
        self.r.execute_command.assert_called_once_with(
            'mysql -u root < create_oozie_db.sql && '
            'rm create_oozie_db.sql')
        _oozie_share_lib.assert_called_once_with(self.r)
        _start_oozie.assert_called_once_with(self.r)

    @mock.patch(PLUGINS_PATH + 'config_helper.get_spark_home')
    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_start_spark_history_server(self, add_provisioning_step,
                                        check_cluster_exists,
                                        set_current_instance_id,
                                        get_spark_home):
        get_spark_home.return_value = '/spark'
        rs.start_spark_history_server(self.instance)
        get_spark_home.assert_called_once_with(self.instance.cluster)
        set_current_instance_id.assert_called_once_with(
            self.instance.instance_id)
        self.r.execute_command.assert_called_once_with(
            'sudo su - -c "bash /spark/sbin/start-history-server.sh" hadoop')

    def test_format_namenode(self):
        rs.format_namenode(self.instance)
        self.remote.execute_command.assert_called_once_with(
            'sudo su - -c "hdfs namenode -format" hadoop')

    @mock.patch('sahara.plugins.vanilla.utils.get_namenode')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_refresh_hadoop_nodes(self, add_provisioning_step,
                                  check_cluster_exists, get_namenode):
        cluster = mock.Mock()
        get_namenode.return_value = self.instance
        rs.refresh_hadoop_nodes(cluster)
        get_namenode.assert_called_once_with(cluster)
        self.remote.execute_command.assert_called_once_with(
            'sudo su - -c "hdfs dfsadmin -refreshNodes" hadoop')

    @mock.patch('sahara.plugins.vanilla.utils.get_resourcemanager')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_refresh_yarn_nodes(self, add_provisioning_step,
                                check_cluster_exists, get_resourcemanager):
        cluster = mock.Mock()
        get_resourcemanager.return_value = self.instance
        rs.refresh_yarn_nodes(cluster)
        get_resourcemanager.assert_called_once_with(cluster)
        self.remote.execute_command.assert_called_once_with(
            'sudo su - -c "yarn rmadmin -refreshNodes" hadoop')

    def test_oozie_share_lib(self):
        cmd_1 = 'sudo su - -c "mkdir /tmp/oozielib && ' \
                'tar zxf /opt/oozie/oozie-sharelib-*.tar.gz -C ' \
                '/tmp/oozielib && ' \
                'hadoop fs -mkdir /user && ' \
                'hadoop fs -mkdir /user/hadoop && ' \
                'hadoop fs -put /tmp/oozielib/share /user/hadoop/ && ' \
                'rm -rf /tmp/oozielib" hadoop'
        cmd_2 = 'sudo su - -c "/opt/oozie/bin/ooziedb.sh ' \
                'create -sqlfile oozie.sql ' \
                '-run Validate DB Connection" hadoop'
        command = [mock.call(cmd_1),
                   mock.call(cmd_2)]
        rs._oozie_share_lib(self.r)
        self.r.execute_command.assert_has_calls(command, any_order=True)

    def test_start_mysql(self):
        rs._start_mysql(self.r)
        self.r.execute_command.assert_called_once_with('/opt/start-mysql.sh')

    def test_start_oozie(self):
        rs._start_oozie(self.r)
        self.r.execute_command.assert_called_once_with(
            'sudo su - -c "/opt/oozie/bin/oozied.sh start" hadoop')

    @mock.patch('sahara.plugins.vanilla.utils.get_namenode')
    @mock.patch('sahara.plugins.vanilla.utils.get_datanodes')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    @mock.patch('sahara.utils.poll_utils.plugin_option_poll')
    def test_await_datanodes(self, plugin_option_poll, add_provisioning_step,
                             check_cluster_exists, get_datanodes,
                             get_namenode):
        cluster = mock.Mock()
        get_datanodes.return_value = ['node1']
        r = mock.Mock()
        remote = mock.Mock(return_value=r)
        remote.__enter__ = remote
        remote.__exit__ = mock.Mock()
        namenode = mock.Mock()
        namenode.remote.return_value = remote
        get_namenode.return_value = namenode
        mess = _('Waiting on 1 datanodes to start up')
        test_data = {'remote': r, 'count': 1}
        timeout = c_helper.DATANODES_STARTUP_TIMEOUT
        rs.await_datanodes(cluster)
        get_datanodes.assert_called_once_with(cluster)
        get_namenode.assert_called_once_with(cluster)
        plugin_option_poll.assert_called_once_with(cluster,
                                                   rs._check_datanodes_count,
                                                   timeout, mess, 1, test_data)

    def test_check_datanodes_count(self):
        self.r.execute_command = mock.Mock(return_value=(0, '1'))
        self.assertEqual(rs._check_datanodes_count(self.r, 0), True)

        self.assertEqual(rs._check_datanodes_count(self.r, 1), True)
        self.r.execute_command.assert_called_once_with(
            'sudo su -lc "hdfs dfsadmin -report" hadoop | '
            'grep \'Live datanodes\|Datanodes available:\' | '
            'grep -o \'[0-9]\+\' | head -n 1')

    def test_hive_create_warehouse_dir(self):
        rs._hive_create_warehouse_dir(self.r)
        self.r.execute_command.assert_called_once_with(
            "sudo su - -c 'hadoop fs -mkdir -p "
            "/user/hive/warehouse' hadoop")

    def test_hive_copy_shared_conf(self):
        dest = '/root/test.xml'
        rs._hive_copy_shared_conf(self.r, dest)
        self.r.execute_command.assert_called_once_with(
            "sudo su - -c 'hadoop fs -mkdir -p /root && "
            "hadoop fs -put /opt/hive/conf/hive-site.xml "
            "/root/test.xml' hadoop")

    def test_hive_create_db(self):
        rs._hive_create_db(self.r)
        self.r.execute_command.assert_called_once_with(
            'mysql -u root < /tmp/create_hive_db.sql')

    def test_hive_metastore_start(self):
        rs._hive_metastore_start(self.r)
        self.r.execute_command.assert_called_once_with(
            "sudo su - -c 'nohup /opt/hive/bin/hive"
            " --service metastore > /dev/null &' hadoop")

    @mock.patch(PLUGINS_PATH + 'utils.get_hive_password')
    @mock.patch(PLUGINS_PATH + 'config_helper.is_mysql_enabled')
    @mock.patch(PLUGINS_PATH + 'run_scripts._hive_metastore_start')
    @mock.patch(PLUGINS_PATH + 'run_scripts._hive_create_db')
    @mock.patch(PLUGINS_PATH + 'run_scripts._start_mysql')
    @mock.patch(PLUGINS_PATH + 'run_scripts._hive_copy_shared_conf')
    @mock.patch(PLUGINS_PATH + 'run_scripts._hive_create_warehouse_dir')
    @mock.patch('sahara.plugins.vanilla.utils.get_oozie')
    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_start_hiveserver_process(self, add_provisioning_step,
                                      check_cluster_exists,
                                      set_current_instance_id, get_oozie,
                                      _hive_create_warehouse_dir,
                                      _hive_copy_shared_conf, _start_mysql,
                                      _hive_create_db, _hive_metastore_start,
                                      is_mysql_enabled, get_hive_password):
        pctx = mock.Mock()
        path = edp.get_hive_shared_conf_path('hadoop')
        is_mysql_enabled.return_value = True
        cluster = self.instance.cluster
        self.instance.cluster.hadoop_version = '2.7.1'
        ng_cluster = self.instance.node_group.cluster
        get_oozie.return_value = None
        sql_script = files.get_file_text(
            'plugins/vanilla/v2_7_1/resources/create_hive_db.sql')
        get_hive_password.return_value = '123'
        pwd_script = sql_script.replace('{{password}}', '123')
        rs.start_hiveserver_process(pctx, self.instance)
        set_current_instance_id.assert_called_once_with(
            self.instance.instance_id)
        _hive_create_warehouse_dir.assert_called_once_with(self.r)
        _hive_copy_shared_conf.assert_called_once_with(self.r, path)
        is_mysql_enabled.assert_called_once_with(pctx, cluster)
        get_oozie.assert_called_once_with(ng_cluster)
        _start_mysql.assert_called_once_with(self.r)
        get_hive_password.assert_called_once_with(cluster)
        self.r.write_file_to.assert_called_once_with(
            '/tmp/create_hive_db.sql', pwd_script)
        _hive_create_db.assert_called_once_with(self.r)
        _hive_metastore_start.assert_called_once_with(self.r)
