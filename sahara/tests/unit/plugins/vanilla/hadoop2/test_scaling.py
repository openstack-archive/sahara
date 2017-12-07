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
from sahara.plugins.vanilla.hadoop2 import config_helper as c_helper
from sahara.plugins.vanilla.hadoop2 import scaling
from sahara.plugins.vanilla.hadoop2 import utils as pu
from sahara.tests.unit import base


class ScalingTest(base.SaharaTestCase):

    PLUGINS_PATH = 'sahara.plugins.vanilla.hadoop2.'

    def setUp(self):
        super(ScalingTest, self).setUp()
        self.cluster = mock.Mock()
        self.instances = mock.Mock()
        self.r = mock.Mock()
        self.r.execute_command = mock.Mock()
        self.instance = mock.Mock()
        self.instance.remote.return_value.__enter__ = mock.Mock(
            return_value=self.r)
        self.instance.remote.return_value.__exit__ = mock.Mock()

    @mock.patch('sahara.swift.swift_helper.install_ssl_certs')
    @mock.patch('sahara.plugins.vanilla.utils.get_resourcemanager')
    @mock.patch(PLUGINS_PATH + 'run_scripts.refresh_zk_servers')
    @mock.patch(PLUGINS_PATH + 'config.configure_zookeeper')
    @mock.patch(PLUGINS_PATH + 'run_scripts.start_dn_nm_processes')
    @mock.patch(PLUGINS_PATH + 'run_scripts.refresh_yarn_nodes')
    @mock.patch(PLUGINS_PATH + 'run_scripts.refresh_hadoop_nodes')
    @mock.patch(PLUGINS_PATH + 'scaling._update_include_files')
    @mock.patch(PLUGINS_PATH + 'config.configure_topology_data')
    @mock.patch(PLUGINS_PATH + 'config.configure_instances')
    def test_scale_cluster(self, configure_instances,
                           configure_topology_data,
                           _update_include_files,
                           refresh_hadoop_nodes,
                           refresh_yarn_nodes,
                           start_dn_nm_processes,
                           configure_zk, refresh_zk,
                           get_resourcemanager,
                           install_ssl_certs):
        get_resourcemanager.return_value = 'node1'
        pctx = mock.Mock()
        scaling.scale_cluster(pctx, self.cluster, self.instances)
        configure_instances.assert_called_once_with(pctx, self.instances)
        _update_include_files.assert_called_once_with(self.cluster)
        refresh_hadoop_nodes.assert_called_once_with(self.cluster)
        get_resourcemanager.assert_called_once_with(self.cluster)
        refresh_yarn_nodes.assert_called_once_with(self.cluster)
        configure_topology_data.assert_called_once_with(pctx, self.cluster)
        start_dn_nm_processes.assert_called_once_with(self.instances)
        install_ssl_certs.assert_called_once_with(self.instances)
        configure_topology_data.assert_called_once_with(pctx, self.cluster)
        configure_zk.assert_called_once_with(self.cluster)
        refresh_zk.assert_called_once_with(self.cluster)

    def test_get_instances_with_service(self):
        ins_1 = mock.Mock()
        ins_1.node_group.node_processes = ['nodename']
        ins_2 = mock.Mock()
        ins_2.node_group.node_processes = ['nodedata']
        instances = [ins_1, ins_2]
        service = 'nodename'
        ret = scaling._get_instances_with_service(instances, service)
        self.assertEqual(ret, [ins_1])

    @mock.patch('sahara.plugins.vanilla.utils.get_nodemanagers')
    @mock.patch('sahara.plugins.vanilla.utils.get_datanodes')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    @mock.patch('sahara.plugins.utils.generate_fqdn_host_names')
    @mock.patch('sahara.plugins.utils.get_instances')
    def test_update_include_files(self, get_instances,
                                  generate_fqdn_host_names,
                                  add_provisioning_step,
                                  check_cluster_exists,
                                  get_datanodes, get_nodemanagers):
        DIR = scaling.HADOOP_CONF_DIR
        host = '1.2.3.4'
        ins_1 = mock.Mock()
        ins_1.id = 'instance_1'
        ins_2 = mock.Mock()
        ins_2.id = 'instance_2'
        ins_3 = mock.Mock()
        ins_3.id = 'instance_3'
        ins_4 = mock.Mock()
        ins_4.id = 'instance_4'
        dec_instances = [ins_1, ins_2]
        get_instances.return_value = [self.instance]
        get_datanodes.return_value = [ins_3]
        get_nodemanagers.return_value = [ins_4]
        generate_fqdn_host_names.return_value = host
        scaling._update_include_files(self.cluster, dec_instances)
        get_instances.assert_called_once_with(self.cluster)
        get_datanodes.assert_called_once_with(self.cluster)
        get_nodemanagers.assert_called_once_with(self.cluster)
        count = generate_fqdn_host_names.call_count
        self.assertEqual(count, 2)
        command_calls = [mock.call(
            'sudo su - -c "echo \'%s\' > %s/dn-include" hadoop' % (
                host, DIR)), mock.call(
            'sudo su - -c "echo \'%s\' > %s/nm-include" hadoop' % (
                host, DIR))]
        self.r.execute_command.assert_has_calls(command_calls, any_order=True)

    @mock.patch('sahara.plugins.vanilla.utils.get_resourcemanager')
    @mock.patch(PLUGINS_PATH + 'run_scripts.refresh_zk_servers')
    @mock.patch(PLUGINS_PATH + 'config.configure_zookeeper')
    @mock.patch(PLUGINS_PATH + 'config.configure_topology_data')
    @mock.patch(PLUGINS_PATH + 'run_scripts.refresh_yarn_nodes')
    @mock.patch(PLUGINS_PATH + 'run_scripts.refresh_hadoop_nodes')
    @mock.patch(PLUGINS_PATH + 'scaling._update_exclude_files')
    @mock.patch(PLUGINS_PATH + 'scaling._clear_exclude_files')
    @mock.patch(PLUGINS_PATH + 'scaling._update_include_files')
    @mock.patch(PLUGINS_PATH + 'scaling._check_datanodes_decommission')
    @mock.patch(PLUGINS_PATH + 'scaling._check_nodemanagers_decommission')
    @mock.patch(PLUGINS_PATH + 'scaling._get_instances_with_service')
    def test_decommission_nodes(self, _get_instances_with_service,
                                _check_nodemanagers_decommission,
                                _check_datanodes_decommission,
                                _update_include_files, _clear_exclude_files,
                                _update_exclude_files, refresh_hadoop_nodes,
                                refresh_yarn_nodes, configure_topology_data,
                                configure_zk, refresh_zk,
                                get_resourcemanager):
        data = 'test_data'
        _get_instances_with_service.return_value = data
        get_resourcemanager.return_value = 'node1'
        pctx = mock.Mock()
        scaling.decommission_nodes(pctx, self.cluster, self.instances)
        get_instances_count = _get_instances_with_service.call_count
        self.assertEqual(get_instances_count, 2)
        _update_exclude_files.assert_called_once_with(self.cluster,
                                                      self.instances)
        refresh_count = refresh_hadoop_nodes.call_count
        self.assertEqual(refresh_count, 2)
        get_resourcemanager.assert_called_once_with(self.cluster)
        refresh_yarn_nodes.assert_called_once_with(self.cluster)
        _check_nodemanagers_decommission.assert_called_once_with(
            self.cluster, data)
        _check_datanodes_decommission.assert_called_once_with(
            self.cluster, data)
        _update_include_files.assert_called_once_with(self.cluster,
                                                      self.instances)
        _clear_exclude_files.assert_called_once_with(self.cluster)
        configure_topology_data.assert_called_once_with(pctx, self.cluster)
        configure_zk.assert_called_once_with(self.cluster, self.instances)
        refresh_zk.assert_called_once_with(self.cluster, self.instances)

    @mock.patch(PLUGINS_PATH + 'scaling._get_instances_with_service')
    @mock.patch('sahara.plugins.utils.generate_fqdn_host_names')
    @mock.patch('sahara.plugins.utils.get_instances')
    def test_update_exclude_files(self, get_instances,
                                  generate_fqdn_host_names,
                                  get_instances_with_service):
        node = mock.Mock()
        get_instances_with_service.return_value = node
        host = '1.2.3.4'
        generate_fqdn_host_names.return_value = host
        get_instances.return_value = [self.instance]
        scaling._update_exclude_files(self.cluster, self.instances)
        service_calls = [mock.call(self.instances, 'datanode'),
                         mock.call(self.instances, 'nodemanager')]
        get_instances_with_service.assert_has_calls(service_calls,
                                                    any_order=True)
        self.assertEqual(generate_fqdn_host_names.call_count, 2)
        get_instances.assert_called_once_with(self.cluster)
        DIR = scaling.HADOOP_CONF_DIR
        command_calls = [mock.call(
            'sudo su - -c "echo \'%s\' > %s/dn-exclude" hadoop' % (
                host, DIR)), mock.call(
            'sudo su - -c "echo \'%s\' > %s/nm-exclude" hadoop' % (
                host, DIR))]
        self.r.execute_command.assert_has_calls(command_calls, any_order=True)

    @mock.patch('sahara.plugins.utils.get_instances')
    def test_clear_exclude_files(self, get_instances):
        get_instances.return_value = [self.instance]
        scaling._clear_exclude_files(self.cluster)
        get_instances.assert_called_once_with(self.cluster)
        DIR = scaling.HADOOP_CONF_DIR
        calls = [mock.call('sudo su - -c "echo > %s/dn-exclude" hadoop' %
                           DIR),
                 mock.call('sudo su - -c "echo > %s/nm-exclude" hadoop' %
                           DIR)]
        self.r.execute_command.assert_has_calls(calls, any_order=True)

    def test_is_decommissioned(self):
        def check_func(cluster):
            statuses = {'status': cluster}
            return statuses
        ins = mock.Mock()
        ins.fqdn.return_value = 'status'
        instances = [ins]
        cluster = 'decommissioned'
        ret = scaling.is_decommissioned(cluster, check_func, instances)
        self.assertEqual(ret, True)

        cluster = 'active'
        ret = scaling.is_decommissioned(cluster, check_func, instances)
        self.assertEqual(ret, False)

    @mock.patch('sahara.utils.poll_utils.plugin_option_poll')
    def test_check_decommission(self, plugin_option_poll):
        check_func = mock.Mock()
        option = mock.Mock()
        is_dec = scaling.is_decommissioned
        mess = _("Wait for decommissioning")
        sample_dict = {'cluster': self.cluster,
                       'check_func': check_func,
                       'instances': self.instances}
        scaling._check_decommission(self.cluster, self.instances,
                                    check_func, option)
        plugin_option_poll.assert_called_once_with(self.cluster, is_dec,
                                                   option, mess, 5,
                                                   sample_dict)

    @mock.patch(PLUGINS_PATH + 'scaling._check_decommission')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_check_nodemanagers_decommission(self, add_provisioning_step,
                                             check_cluster_exists,
                                             _check_decommission):
        timeout = c_helper.NODEMANAGERS_DECOMMISSIONING_TIMEOUT
        status = pu.get_nodemanagers_status
        scaling._check_nodemanagers_decommission(self.cluster, self.instances)
        _check_decommission.assert_called_once_with(self.cluster,
                                                    self.instances,
                                                    status, timeout)

    @mock.patch(PLUGINS_PATH + 'scaling._check_decommission')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_check_datanodes_decommission(self, add_provisioning_step,
                                          check_cluster_exists,
                                          _check_decommission):
        timeout = c_helper.DATANODES_DECOMMISSIONING_TIMEOUT
        status = pu.get_datanodes_status
        scaling._check_datanodes_decommission(self.cluster, self.instances)
        _check_decommission.assert_called_once_with(self.cluster,
                                                    self.instances,
                                                    status, timeout)
