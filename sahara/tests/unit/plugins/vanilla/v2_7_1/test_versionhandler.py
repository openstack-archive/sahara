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
import six

from sahara.plugins.vanilla.hadoop2 import run_scripts as run
from sahara.plugins.vanilla.hadoop2 import starting_scripts as s_scripts
from sahara.plugins.vanilla.v2_7_1.edp_engine import EdpOozieEngine
from sahara.plugins.vanilla.v2_7_1.edp_engine import EdpSparkEngine
from sahara.plugins.vanilla.v2_7_1 import versionhandler as v_h
from sahara.tests.unit import base
from sahara.tests.unit import testutils


class TestConfig(object):
    def __init__(self, applicable_target, name, default_value):
        self.applicable_target = applicable_target
        self.name = name
        self.default_value = default_value


class VersionHandlerTest(base.SaharaTestCase):
    plugin_path = 'sahara.plugins.vanilla.'
    plugin_hadoop2_path = 'sahara.plugins.vanilla.hadoop2.'

    def setUp(self):
        super(VersionHandlerTest, self).setUp()
        self.cluster = mock.Mock()
        self.vh = v_h.VersionHandler()

    def test_get_plugin_configs(self):
        self.vh.pctx['all_confs'] = 'haha'
        conf = self.vh.get_plugin_configs()
        self.assertEqual(conf, 'haha')

    def test_get_node_processes(self):
        processes = self.vh.get_node_processes()
        for k, v in six.iteritems(processes):
            for p in v:
                self.assertIsInstance(p, str)

    @mock.patch(plugin_hadoop2_path +
                'validation.validate_cluster_creating')
    def test_validate(self, validate_create):
        self.vh.pctx = mock.Mock()
        self.vh.validate(self.cluster)
        validate_create.assert_called_once_with(self.vh.pctx,
                                                self.cluster)

    @mock.patch(plugin_path +
                'v2_7_1.versionhandler.VersionHandler.update_infra')
    def test_update_infra(self, update_infra):
        self.vh.update_infra(self.cluster)
        update_infra.assert_called_once_with(self.cluster)

    @mock.patch(plugin_hadoop2_path + 'config.configure_cluster')
    def test_configure_cluster(self, configure_cluster):
        self.vh.pctx = mock.Mock()
        self.vh.configure_cluster(self.cluster)
        configure_cluster.assert_called_once_with(self.vh.pctx, self.cluster)

    @mock.patch('sahara.swift.swift_helper.install_ssl_certs')
    @mock.patch(plugin_hadoop2_path + 'keypairs.provision_keypairs')
    @mock.patch('sahara.plugins.utils.get_instances')
    @mock.patch('sahara.utils.cluster.get_instances')
    def test_start_cluster(self, c_get_instances, u_get_instances,
                           provision_keypairs, install_ssl_certs):
        self.vh.pctx = mock.Mock()
        instances = mock.Mock()
        s_scripts.start_namenode = mock.Mock()
        s_scripts.start_secondarynamenode = mock.Mock()
        s_scripts.start_resourcemanager = mock.Mock()
        s_scripts.start_historyserver = mock.Mock()
        s_scripts.start_oozie = mock.Mock()
        s_scripts.start_hiveserver = mock.Mock()
        s_scripts.start_spark = mock.Mock()
        c_get_instances.return_value = instances
        u_get_instances.return_value = instances
        run.await_datanodes = mock.Mock()
        run.start_dn_nm_processes = mock.Mock()
        self.vh._set_cluster_info = mock.Mock()
        self.vh.start_cluster(self.cluster)
        provision_keypairs.assert_called_once_with(self.cluster)
        s_scripts.start_namenode.assert_called_once_with(self.cluster)
        s_scripts.start_secondarynamenode.assert_called_once_with(self.cluster)
        s_scripts.start_resourcemanager.assert_called_once_with(self.cluster)
        s_scripts.start_historyserver.assert_called_once_with(self.cluster)
        s_scripts.start_oozie.assert_called_once_with(self.vh.pctx,
                                                      self.cluster)
        s_scripts.start_hiveserver.assert_called_once_with(self.vh.pctx,
                                                           self.cluster)
        s_scripts.start_spark.assert_called_once_with(self.cluster)
        run.start_dn_nm_processes.assert_called_once_with(instances)
        run.await_datanodes.assert_called_once_with(self.cluster)
        install_ssl_certs.assert_called_once_with(instances)
        self.vh._set_cluster_info.assert_called_once_with(self.cluster)

    @mock.patch(plugin_hadoop2_path + 'scaling.decommission_nodes')
    def test_decommission_nodes(self, decommission_nodes):
        self.vh.pctx = mock.Mock()
        cluster = mock.Mock()
        instances = mock.Mock()
        self.vh.decommission_nodes(cluster, instances)
        decommission_nodes.assert_called_once_with(self.vh.pctx,
                                                   cluster,
                                                   instances)

    @mock.patch(plugin_hadoop2_path +
                'validation.validate_additional_ng_scaling')
    @mock.patch(plugin_hadoop2_path +
                'validation.validate_existing_ng_scaling')
    def test_validate_scaling(self, vls, vla):
        self.vh.pctx['all_confs'] = [TestConfig('HDFS', 'dfs.replication', -1)]
        ng1 = testutils.make_ng_dict('ng1', '40', ['namenode'], 1)
        ng2 = testutils.make_ng_dict('ng2', '41', ['datanode'], 2)
        ng3 = testutils.make_ng_dict('ng3', '42', ['datanode'], 3)
        additional = [ng2['id'], ng3['id']]
        existing = {ng2['id']: 1}
        cluster = testutils.create_cluster('test-cluster', 'tenant1', 'fake',
                                           '0.1', [ng1, ng2, ng3])
        self.vh.validate_scaling(cluster, existing, additional)
        vla.assert_called_once_with(cluster, additional)
        vls.assert_called_once_with(self.vh.pctx, cluster, existing)

    @mock.patch(plugin_hadoop2_path + 'scaling.scale_cluster')
    @mock.patch(plugin_hadoop2_path + 'keypairs.provision_keypairs')
    def test_scale_cluster(self, provision_keypairs, scale_cluster):
        self.vh.pctx = mock.Mock()
        instances = mock.Mock()
        self.vh.scale_cluster(self.cluster, instances)
        provision_keypairs.assert_called_once_with(self.cluster,
                                                   instances)
        scale_cluster.assert_called_once_with(self.vh.pctx,
                                              self.cluster,
                                              instances)

    @mock.patch("sahara.conductor.API.cluster_update")
    @mock.patch("sahara.context.ctx")
    @mock.patch(plugin_path + 'utils.get_namenode')
    @mock.patch(plugin_path + 'utils.get_resourcemanager')
    @mock.patch(plugin_path + 'utils.get_historyserver')
    @mock.patch(plugin_path + 'utils.get_oozie')
    @mock.patch(plugin_path + 'utils.get_spark_history_server')
    def test_set_cluster_info(self, get_spark_history_server, get_oozie,
                              get_historyserver, get_resourcemanager,
                              get_namenode, ctx, cluster_update):
        get_spark_history_server.return_value.management_ip = '1.2.3.0'
        get_oozie.return_value.get_ip_or_dns_name = mock.Mock(
            return_value='1.2.3.1')
        get_historyserver.return_value.get_ip_or_dns_name = mock.Mock(
            return_value='1.2.3.2')
        get_resourcemanager.return_value.get_ip_or_dns_name = mock.Mock(
            return_value='1.2.3.3')
        get_namenode.return_value.get_ip_or_dns_name = mock.Mock(
            return_value='1.2.3.4')
        get_namenode.return_value.hostname = mock.Mock(
            return_value='testnode')
        self.vh._set_cluster_info(self.cluster)
        info = {'YARN': {
            'Web UI': 'http://1.2.3.3:8088',
            'ResourceManager': 'http://1.2.3.3:8032'
            },
            'HDFS': {
                'Web UI': 'http://1.2.3.4:50070',
                'NameNode': 'hdfs://testnode:9000'
            },
            'JobFlow': {
                'Oozie': 'http://1.2.3.1:11000'
            },
            'MapReduce JobHistory Server': {
                'Web UI': 'http://1.2.3.2:19888'
            },
            'Apache Spark': {
                'Spark UI': 'http://1.2.3.0:4040',
                'Spark History Server UI': 'http://1.2.3.0:18080'
            }
        }
        cluster_update.assert_called_once_with(ctx(), self.cluster,
                                               {'info': info})

    @mock.patch("sahara.service.edp.job_utils.get_plugin")
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('os.path.join')
    def test_get_edp_engine(self, join, get_instance, get_plugin):
        job_type = ''
        ret = self.vh.get_edp_engine(self.cluster, job_type)
        self.assertEqual(ret, None)

        job_type = 'Java'
        ret = self.vh.get_edp_engine(self.cluster, job_type)
        self.assertIsInstance(ret, EdpOozieEngine)

        job_type = 'Spark'
        ret = self.vh.get_edp_engine(self.cluster, job_type)
        self.assertIsInstance(ret, EdpSparkEngine)

    def test_get_edp_job_types(self):
        job_types = ['Hive', 'Java', 'MapReduce',
                     'MapReduce.Streaming', 'Pig', 'Shell', 'Spark']
        self.assertEqual(self.vh.get_edp_job_types(), job_types)

    def test_get_edp_config_hints(self):
        job_type = 'Java'
        ret = {'job_config': {'args': [], 'configs': []}}
        self.assertEqual(self.vh.get_edp_config_hints(job_type), ret)

    @mock.patch(plugin_hadoop2_path + 'utils.delete_oozie_password')
    @mock.patch(plugin_hadoop2_path + 'keypairs.drop_key')
    def test_on_terminate_cluster(self, delete_oozie_password, drop_key):
        self.vh.on_terminate_cluster(self.cluster)
        delete_oozie_password.assert_called_once_with(self.cluster)
        drop_key.assert_called_once_with(self.cluster)

    @mock.patch(plugin_hadoop2_path + 'config.get_open_ports')
    def test_get_open_ports(self, get_open_ports):
        node_group = mock.Mock()
        self.vh.get_open_ports(node_group)
        get_open_ports.assert_called_once_with(node_group)

    @mock.patch(plugin_hadoop2_path +
                'recommendations_utils.recommend_configs')
    def test_recommend_configs(self, recommend_configs):
        scaling = mock.Mock()
        configs = mock.Mock()
        self.vh.pctx['all_confs'] = configs
        self.vh.recommend_configs(self.cluster, scaling)
        recommend_configs.assert_called_once_with(self.cluster,
                                                  configs,
                                                  scaling)
