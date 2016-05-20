# Copyright (c) 2016 Mirantis Inc.
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

from sahara.plugins.cdh.v5_5_0 import deploy
from sahara.tests.unit import base


class DeployCDHV550(base.SaharaTestCase):

    def setUp(self):
        super(DeployCDHV550, self).setUp()
        self.master = mock.MagicMock()
        self.master.node_group.node_processes = [
            "HDFS_NAMENODE", "YARN_RESOURCEMANAGER", "CLOUDERA_MANAGER",
            "SENTRY_SERVER", "YARN_NODEMANAGER", "ZOOKEEPER_SERVER",
            "OOZIE_SERVER", "YARN_JOBHISTORY", "HDFS_SECONDARYNAMENODE",
            "HIVE_METASTORE", "HIVE_SERVER2", "SPARK_YARN_HISTORY_SERVER",
            "HBASE_MASTER", "HBASE_REGIONSERVER", "HUE_SERVER", "KMS",
            "FLUME_AGENT", "SOLR_SERVER", "SQOOP_SERVER", "IMPALA_STATESTORE",
            "IMPALA_CATALOGSERVER", "IMPALAD", "KEY_VALUE_STORE_INDEXER",
        ]
        self.worker = mock.MagicMock()
        self.worker.node_group.node_processes = [
            "HDFS_DATANODE", "HDFS_JOURNALNODE", "JOURNALNODE",
            "YARN_NODEMANAGER", "YARN_STANDBYRM",
        ]
        self.instances = [self.master, self.worker]
        self.cluster = mock.MagicMock()

        self.is_cdh_exists = mock.patch(
            "sahara.plugins.cdh.commands.is_pre_installed_cdh",
            return_value=False)
        self.is_cdh_exists.start()
        self._create_facade = mock.patch(
            "sahara.db.sqlalchemy.api._create_facade_lazily")
        self._create_facade.start()

    def tearDown(self):
        self.is_cdh_exists.stop()
        self._create_facade.stop()
        super(DeployCDHV550, self).tearDown()

    @mock.patch("sahara.plugins.utils.get_instances")
    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy.CU")
    def test_configure_cluster(self, mock_cu, mock_get_instances):
        mock_get_instances.return_value = self.instances

        deploy.configure_cluster(self.cluster)

        mock_cu.pu.configure_os.assert_called_once_with(self.instances)
        mock_cu.pu.install_packages.assert_called_once_with(self.instances,
                                                            deploy.PACKAGES)
        mock_cu.pu.start_cloudera_agents.assert_called_once_with(
            self.instances)
        mock_cu.pu.start_cloudera_manager.assert_called_once_with(self.cluster)
        mock_cu.update_cloudera_password.assert_called_once_with(self.cluster)
        mock_cu.await_agents.assert_called_once_with(self.cluster,
                                                     self.instances)
        mock_cu.create_mgmt_service.assert_called_once_with(self.cluster)
        mock_cu.create_services.assert_called_once_with(self.cluster)
        mock_cu.configure_services.assert_called_once_with(self.cluster)
        mock_cu.configure_instances.assert_called_once_with(self.instances,
                                                            self.cluster)
        mock_cu.deploy_configs.assert_called_once_with(self.cluster)

    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy.CU")
    def test__start_roles(self, mock_cu):

        deploy._start_roles(self.cluster, self.instances)

        mock_cu.get_service_by_role.assert_any_call('DATANODE',
                                                    instance=self.worker)
        mock_cu.get_service_by_role.assert_any_call('NODEMANAGER',
                                                    instance=self.master)
        mock_cu.get_service_by_role.assert_any_call('NODEMANAGER',
                                                    instance=self.worker)
        self.assertEqual(mock_cu.start_roles.call_count, 3)

    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy._start_roles")
    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy.CU")
    def test_scale_cluster(self, mock_cu, mock__start_roles):
        deploy.scale_cluster(self.cluster, None)
        self.assertEqual(mock_cu.call_count, 0)
        self.assertEqual(mock__start_roles.call_count, 0)

        deploy.scale_cluster(self.cluster, self.instances)

        mock_cu.pu.configure_os.assert_called_once_with(self.instances)
        mock_cu.pu.install_packages.assert_called_once_with(self.instances,
                                                            deploy.PACKAGES)
        mock_cu.pu.start_cloudera_agents.assert_called_once_with(
            self.instances)
        mock_cu.await_agents.assert_called_once_with(self.cluster,
                                                     self.instances)
        mock_cu.configure_instances.assert_called_once_with(self.instances,
                                                            self.cluster)
        mock_cu.update_configs.assert_called_once_with(self.instances)
        mock_cu.pu.configure_swift.assert_called_once_with(self.cluster,
                                                           self.instances)
        mock_cu.refresh_datanodes.assert_called_once_with(self.cluster)
        mock__start_roles.assert_called_once_with(self.cluster,
                                                  self.instances)

    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy.CU")
    def test_decommission_cluster(self, mock_cu):
        deploy.decommission_cluster(self.cluster, self.instances)
        dns = []
        nms = []
        for i in self.instances:
            if 'HDFS_DATANODE' in i.node_group.node_processes:
                dns.append(mock_cu.pu.get_role_name(i, 'DATANODE'))
            if 'YARN_NODEMANAGER' in i.node_group.node_processes:
                nms.append(mock_cu.pu.get_role_name(i, 'NODEMANAGER'))
        mock_cu.decommission_nodes.assert_any_call(
            self.cluster, 'DATANODE', dns)
        mock_cu.decommission_nodes.assert_any_call(
            self.cluster, 'NODEMANAGER', nms)
        mock_cu.delete_instances.assert_called_once_with(self.cluster,
                                                         self.instances)
        mock_cu.refresh_datanodes.assert_called_once_with(self.cluster)
        mock_cu.refresh_yarn_nodes.assert_called_once_with(self.cluster)

    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy.CU")
    def test__prepare_cluster(self, mock_cu):
        deploy._prepare_cluster(self.cluster)

        mock_cu.pu.install_extjs.assert_called_once_with(self.cluster)
        mock_cu.pu.configure_hive.assert_called_once_with(self.cluster)
        mock_cu.pu.configure_sentry.assert_called_once_with(self.cluster)

    @mock.patch("sahara.service.edp.hdfs_helper.create_hbase_common_lib")
    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy.CU")
    def test__finish_cluster_starting(self, mock_cu, mock_create_hbase):
        deploy._finish_cluster_starting(self.cluster)
        mock_cu.pu.put_hive_hdfs_xml.assert_called_once_with(self.cluster)
        self.assertTrue(mock_create_hbase.called)
        mock_cu.start_service.assert_called_once_with(
            mock_cu.get_service_by_role('AGENT', self.cluster))

    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy._finish_cluster_starting")
    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy._prepare_cluster")
    @mock.patch("sahara.plugins.cdh.v5_5_0.deploy.CU")
    def test_start_cluster(self, mock_cu, mock_prepare, mock_finish):
        jns_count = 0
        for i in self.instances:
            if "HDFS_JOURNALNODE" in i.node_group.node_processes:
                jns_count += 1
        mock_cu.pu.get_jns.return_value.__len__.return_value = jns_count

        deploy.start_cluster(self.cluster)

        mock_prepare.assert_called_once_with(self.cluster)
        mock_cu.first_run.assert_called_once_with(self.cluster)
        mock_cu.pu.configure_swift.assert_called_once_with(self.cluster)
        if jns_count > 0:
            mock_cu.enable_namenode_ha.assert_called_once_with(self.cluster)
            mock_cu.update_role_config.assert_any_call(
                mock_cu.pu.get_secondarynamenode(self.cluster),
                'HDFS_NAMENODE'
            )
        mock_cu.enable_resourcemanager_ha.assert_called_once_with(self.cluster)
        mock_cu.update_role_config.assert_any_call(
            mock_cu.pu.get_stdb_rm(self.cluster), 'YARN_STANDBYRM')
        mock_finish.assert_called_once_with(self.cluster)

    def test_get_open_ports(self):
        master_ports = [
            9000,
            7180, 7182, 7183, 7432, 7184, 8084, 8086, 10101,
            9997, 9996, 8087, 9998, 9999, 8085, 9995, 9994,
            8020, 8022, 50070, 50470,
            50090, 50495,
            8030, 8031, 8032, 8033, 8088,
            8040, 8041, 8042,
            10020, 19888,
            9083,
            10000,
            8888,
            11000, 11001,
            18088,
            2181, 3181, 4181, 9010,
            60000,
            60020,
            41414,
            8038,
            8983, 8984,
            8005, 12000,
            25020, 26000,
            25010, 24000,
            21050, 21000, 23000, 25000, 28000, 22000,
            16000, 16001
        ]
        deploy.get_open_ports(self.master.node_group)
        self.assertItemsEqual(master_ports,
                              deploy.get_open_ports(self.master.node_group))
        worker_ports = [
            9000,
            50010, 1004, 50075, 1006, 50020,
            8480, 8481, 8485,
            8040, 8041, 8042,
            8030, 8031, 8032, 8033, 8088
        ]
        self.assertItemsEqual(worker_ports,
                              deploy.get_open_ports(self.worker.node_group))
