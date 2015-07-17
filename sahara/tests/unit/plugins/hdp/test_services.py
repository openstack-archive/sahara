# Copyright (c) 2013 Hortonworks, Inc.
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

from sahara import exceptions as e
from sahara.plugins import exceptions as ex
from sahara.plugins.hdp.versions import versionhandlerfactory as vhf
from sahara.tests.unit import base
from sahara.tests.unit.plugins.hdp import hdp_test_base

versions = ['2.0.6']


class ServicesTest(base.SaharaTestCase):
    # TODO(jspeidel): test remaining service functionality which isn't
    # tested by coarser grained unit tests.

    def get_services_processor(self, version='2.0.6'):
        handler = (vhf.VersionHandlerFactory.get_instance().
                   get_version_handler(version))
        s = handler.get_services_processor()
        return s

    def test_create_hdfs_service(self):
        for version in versions:
            s = self.get_services_processor(version)
            service = s.create_service('HDFS')
            self.assertEqual('HDFS', service.name)
            expected_configs = set(['global', 'core-site', 'hdfs-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertTrue(service.is_mandatory())

    def test_hdp2_hdfs_service_register_urls(self):
        s = self.get_services_processor('2.0.6')
        service = s.create_service('HDFS')
        cluster_spec = mock.Mock()
        cluster_spec.configurations = {
            'core-site': {
                'fs.defaultFS': 'hdfs://not_expected.com:9020'
            },
            'hdfs-site': {
                'dfs.namenode.http-address': 'http://not_expected.com:10070'
            }
        }
        instance_mock = mock.Mock()
        instance_mock.management_ip = '127.0.0.1'
        cluster_spec.determine_component_hosts = mock.Mock(
            return_value=[instance_mock])
        cluster = mock.Mock(cluster_configs={}, name="hdp")
        url_info = {}
        url_info = service.register_service_urls(cluster_spec, url_info,
                                                 cluster)
        self.assertEqual(url_info['HDFS']['Web UI'],
                         'http://127.0.0.1:10070')
        self.assertEqual(url_info['HDFS']['NameNode'],
                         'hdfs://127.0.0.1:9020')

    def test_hdp2_ha_hdfs_service_register_urls(self):
        s = self.get_services_processor('2.0.6')
        service = s.create_service('HDFS')
        cluster_spec = mock.Mock()
        cluster_spec.configurations = {
            'core-site': {
                'fs.defaultFS': 'hdfs://not_expected.com:9020'
            },
            'hdfs-site': {
                'dfs.namenode.http-address': 'http://not_expected.com:10070'
            }
        }
        instance_mock = mock.Mock()
        instance_mock.management_ip = '127.0.0.1'
        cluster_spec.determine_component_hosts = mock.Mock(
            return_value=[instance_mock])
        cluster = mock.Mock(cluster_configs={'HDFSHA': {'hdfs.nnha': True}})
        cluster.name = "hdp-cluster"
        url_info = {}
        url_info = service.register_service_urls(cluster_spec, url_info,
                                                 cluster)
        self.assertEqual(url_info['HDFS']['Web UI'],
                         'http://127.0.0.1:10070')
        self.assertEqual(url_info['HDFS']['NameNode'],
                         'hdfs://127.0.0.1:9020')
        self.assertEqual(url_info['HDFS']['NameService'],
                         'hdfs://hdp-cluster')

    def test_create_mr2_service(self):
        s = self.get_services_processor('2.0.6')
        service = s.create_service('MAPREDUCE2')
        self.assertEqual('MAPREDUCE2', service.name)
        expected_configs = set(['global', 'core-site', 'mapred-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())

    def test_hdp2_mr2_service_register_urls(self):
        s = self.get_services_processor('2.0.6')
        service = s.create_service('MAPREDUCE2')
        cluster_spec = mock.Mock()
        cluster_spec.configurations = {
            'mapred-site': {
                'mapreduce.jobhistory.address':
                'hdfs://not_expected.com:10300',
                'mapreduce.jobhistory.webapp.address':
                'http://not_expected.com:10030'
            }
        }
        instance_mock = mock.Mock()
        instance_mock.management_ip = '127.0.0.1'
        cluster_spec.determine_component_hosts = mock.Mock(
            return_value=[instance_mock])
        url_info = {}
        url_info = service.register_service_urls(cluster_spec, url_info,
                                                 mock.Mock())
        self.assertEqual(url_info['MapReduce2']['Web UI'],
                         'http://127.0.0.1:10030')
        self.assertEqual(url_info['MapReduce2']['History Server'],
                         '127.0.0.1:10300')

    def test_create_hive_service(self):
        for version in versions:
            s = self.get_services_processor(version)
            service = s.create_service('HIVE')
            self.assertEqual('HIVE', service.name)
            expected_configs = set(['global', 'core-site', 'hive-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertFalse(service.is_mandatory())

    def test_create_webhcat_service(self):
        for version in versions:
            s = self.get_services_processor(version)
            service = s.create_service('WEBHCAT')
            self.assertEqual('WEBHCAT', service.name)
            expected_configs = set(['global', 'core-site', 'webhcat-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertFalse(service.is_mandatory())

    def test_create_zk_service(self):
        for version in versions:
            s = self.get_services_processor()
            service = s.create_service('ZOOKEEPER')
            self.assertEqual('ZOOKEEPER', service.name)
            expected_configs = set(['global', 'core-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertTrue(service.is_mandatory())

    def test_create_oozie_service(self):
        for version in versions:
            s = self.get_services_processor()
            service = s.create_service('OOZIE')
            self.assertEqual('OOZIE', service.name)
            expected_configs = set(['global', 'core-site', 'oozie-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertFalse(service.is_mandatory())

    def test_oozie_service_register_urls(self):
        for version in versions:
            s = self.get_services_processor(version)
            service = s.create_service('OOZIE')
            cluster_spec = mock.Mock()
            cluster_spec.configurations = {
                'oozie-site': {
                    'oozie.base.url': 'hdfs://not_expected.com:21000'
                }
            }
            instance_mock = mock.Mock()
            instance_mock.management_ip = '127.0.0.1'
            cluster_spec.determine_component_hosts = mock.Mock(
                return_value=[instance_mock])
            url_info = {}
            url_info = service.register_service_urls(cluster_spec, url_info,
                                                     mock.Mock())
            self.assertEqual('http://127.0.0.1:21000',
                             url_info['JobFlow']['Oozie'])

    def test_create_ganglia_service(self):
        for version in versions:
            s = self.get_services_processor(version)
            service = s.create_service('GANGLIA')
            self.assertEqual('GANGLIA', service.name)
            expected_configs = set(['global', 'core-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertFalse(service.is_mandatory())

    def test_create_ambari_service(self):
        for version in versions:
            s = self.get_services_processor(version)
            service = s.create_service('AMBARI')
            self.assertEqual('AMBARI', service.name)
            expected_configs = set(['global', 'core-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertTrue(service.is_mandatory())

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_hdp2_create_sqoop_service(self, patched):
        s = self.get_services_processor('2.0.6')
        service = s.create_service('SQOOP')
        self.assertEqual('SQOOP', service.name)
        expected_configs = set(['global', 'core-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

        # ensure that hdfs and mr clients are added implicitly
        master_host = hdp_test_base.TestServer(
            'master.novalocal', 'master', '11111', 3,
            '111.11.1111', '222.11.1111')
        master_ng = hdp_test_base.TestNodeGroup(
            'master', [master_host], ["NAMENODE", "RESOURCEMANAGER",
                                      "HISTORYSERVER", "SECONDARY_NAMENODE",
                                      "NODEMANAGER", "DATANODE",
                                      "AMBARI_SERVER", "ZOOKEEPER_SERVER"])
        sqoop_host = hdp_test_base.TestServer(
            'sqoop.novalocal', 'sqoop', '11111', 3,
            '111.11.1111', '222.11.1111')
        sqoop_ng = hdp_test_base.TestNodeGroup(
            'sqoop', [sqoop_host], ["SQOOP"])
        cluster = hdp_test_base.TestCluster([master_ng, sqoop_ng])

        cluster_spec = hdp_test_base.create_clusterspec(hdp_version='2.0.6')
        cluster_spec.create_operational_config(cluster, [])

        components = cluster_spec.get_node_groups_containing_component(
            'SQOOP')[0].components
        self.assertIn('HDFS_CLIENT', components)
        self.assertIn('MAPREDUCE2_CLIENT', components)

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_create_hbase_service(self, patched):
        s = self.get_services_processor()
        service = s.create_service('HBASE')
        self.assertEqual('HBASE', service.name)
        expected_configs = set(['global', 'core-site', 'hbase-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

        cluster = self._create_hbase_cluster()

        cluster_spec = hdp_test_base.create_clusterspec()
        cluster_spec.create_operational_config(cluster, [])

        components = cluster_spec.get_node_groups_containing_component(
            'HBASE_MASTER')[0].components
        self.assertIn('HDFS_CLIENT', components)

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_create_hdp2_hbase_service(self, patched):
        for version in versions:
            s = self.get_services_processor(version=version)
            service = s.create_service('HBASE')
            self.assertEqual('HBASE', service.name)
            expected_configs = set(['global', 'core-site', 'hbase-site'])
            self.assertEqual(expected_configs,
                             expected_configs & service.configurations)
            self.assertFalse(service.is_mandatory())

            cluster = self._create_hbase_cluster()

            cluster_spec = hdp_test_base.create_clusterspec(
                hdp_version=version)
            cluster_spec.create_operational_config(cluster, [])

            components = cluster_spec.get_node_groups_containing_component(
                'HBASE_MASTER')[0].components
            self.assertIn('HDFS_CLIENT', components)

    def test_create_yarn_service(self):
        s = self.get_services_processor(version='2.0.6')
        service = s.create_service('YARN')
        self.assertEqual('YARN', service.name)
        expected_configs = set(['global', 'core-site', 'yarn-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_hbase_properties(self, patched):
        for version in versions:
            cluster = self._create_hbase_cluster()

            cluster_spec = hdp_test_base.create_clusterspec(
                hdp_version=version)
            cluster_spec.create_operational_config(cluster, [])
            s = self.get_services_processor(version=version)
            service = s.create_service('HBASE')

            ui_handlers = {}
            service.register_user_input_handlers(ui_handlers)
            ui_handlers['hbase-site/hbase.rootdir'](
                hdp_test_base.TestUserInput(
                    hdp_test_base.TestUserInputConfig(
                        '', '', 'hbase-site/hbase.rootdir'),
                    "hdfs://%NN_HOST%:99/some/other/dir"),
                cluster_spec.configurations)
            self.assertEqual(
                "hdfs://%NN_HOST%:99/some/other/dir",
                cluster_spec.configurations['hbase-site']['hbase.rootdir'])
            self.assertEqual(
                "/some/other/dir",
                cluster_spec.configurations['global']['hbase_hdfs_root_dir'])

            self.assertRaises(
                e.InvalidDataException,
                ui_handlers['hbase-site/hbase.rootdir'],
                hdp_test_base.TestUserInput(
                    hdp_test_base.TestUserInputConfig(
                        '', '', 'hbase-site/hbase.rootdir'),
                    "badprotocol://%NN_HOST%:99/some/other/dir"),
                cluster_spec.configurations)

            ui_handlers['hbase-site/hbase.tmp.dir'](
                hdp_test_base.TestUserInput(
                    hdp_test_base.TestUserInputConfig(
                        '', '', 'hbase-site/hbase.tmp.dir'),
                    "/some/dir"),
                cluster_spec.configurations)
            self.assertEqual(
                "/some/dir",
                cluster_spec.configurations['hbase-site']['hbase.tmp.dir'])
            self.assertEqual(
                "/some/dir",
                cluster_spec.configurations['global']['hbase_tmp_dir'])
            ui_handlers[
                'hbase-site/hbase.regionserver.global.memstore.upperLimit'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hbase.regionserver.global.'
                                'memstore.upperLimit'),
                        "111"),
                    cluster_spec.configurations)
            self.assertEqual(
                "111",
                cluster_spec.configurations['hbase-site'][
                    'hbase.regionserver.global.memstore.upperLimit'])
            self.assertEqual(
                "111",
                cluster_spec.configurations['global'][
                    'regionserver_memstore_upperlimit'])
            ui_handlers[
                'hbase-site/hbase.hstore.blockingStoreFiles'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '',
                            'hbase-site/hbase.hstore.blockingStoreFiles'),
                        "112"),
                    cluster_spec.configurations)
            self.assertEqual("112", cluster_spec.configurations['hbase-site'][
                             'hbase.hstore.blockingStoreFiles'])
            self.assertEqual("112", cluster_spec.configurations['global'][
                             'hstore_blockingstorefiles'])
            ui_handlers[
                'hbase-site/hbase.hstore.compactionThreshold'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '',
                            'hbase-site/hbase.hstore.compactionThreshold'),
                        "113"),
                    cluster_spec.configurations)
            self.assertEqual("113", cluster_spec.configurations['hbase-site'][
                             'hbase.hstore.compactionThreshold'])
            self.assertEqual("113", cluster_spec.configurations['global'][
                             'hstore_compactionthreshold'])
            ui_handlers[
                'hbase-site/hfile.block.cache.size'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hfile.block.cache.size'),
                        "114"),
                    cluster_spec.configurations)
            self.assertEqual("114", cluster_spec.configurations['hbase-site'][
                             'hfile.block.cache.size'])
            self.assertEqual("114", cluster_spec.configurations['global'][
                             'hfile_blockcache_size'])
            ui_handlers[
                'hbase-site/hbase.hregion.max.filesize'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hbase.hregion.max.filesize'),
                        "115"),
                    cluster_spec.configurations)
            self.assertEqual("115", cluster_spec.configurations['hbase-site'][
                             'hbase.hregion.max.filesize'])
            self.assertEqual("115", cluster_spec.configurations['global'][
                             'hstorefile_maxsize'])
            ui_handlers[
                'hbase-site/hbase.regionserver.handler.count'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '',
                            'hbase-site/hbase.regionserver.handler.count'),
                        "116"),
                    cluster_spec.configurations)
            self.assertEqual("116", cluster_spec.configurations['hbase-site'][
                             'hbase.regionserver.handler.count'])
            self.assertEqual("116", cluster_spec.configurations['global'][
                             'regionserver_handlers'])
            ui_handlers[
                'hbase-site/hbase.hregion.majorcompaction'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '',
                            'hbase-site/hbase.hregion.majorcompaction'),
                        "117"),
                    cluster_spec.configurations)
            self.assertEqual("117", cluster_spec.configurations['hbase-site'][
                             'hbase.hregion.majorcompaction'])
            self.assertEqual("117", cluster_spec.configurations['global'][
                             'hregion_majorcompaction'])
            ui_handlers[
                'hbase-site/hbase.regionserver.global.memstore.lowerLimit'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hbase.regionserver.global.'
                                'memstore.lowerLimit'),
                        "118"),
                    cluster_spec.configurations)
            self.assertEqual("118", cluster_spec.configurations['hbase-site'][
                             'hbase.regionserver.global.memstore.lowerLimit'])
            self.assertEqual("118", cluster_spec.configurations['global'][
                             'regionserver_memstore_lowerlimit'])
            ui_handlers[
                'hbase-site/hbase.hregion.memstore.block.multiplier'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hbase.hregion.memstore.block.'
                                'multiplier'),
                        "119"),
                    cluster_spec.configurations)
            self.assertEqual("119", cluster_spec.configurations['hbase-site'][
                             'hbase.hregion.memstore.block.multiplier'])
            self.assertEqual("119", cluster_spec.configurations['global'][
                             'hregion_blockmultiplier'])
            ui_handlers[
                'hbase-site/hbase.hregion.memstore.mslab.enabled'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hbase.hregion.memstore.mslab.'
                                'enabled'),
                        "false"),
                    cluster_spec.configurations)
            self.assertEqual("false", cluster_spec.configurations['hbase-site']
                             ['hbase.hregion.memstore.mslab.enabled'])
            self.assertEqual("false", cluster_spec.configurations['global'][
                             'regionserver_memstore_lab'])
            ui_handlers[
                'hbase-site/hbase.hregion.memstore.flush.size'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hbase.hregion.memstore.flush.'
                                'size'),
                        "120"),
                    cluster_spec.configurations)
            self.assertEqual("120", cluster_spec.configurations['hbase-site'][
                             'hbase.hregion.memstore.flush.size'])
            if version == '1.3.2':
                self.assertEqual("120", cluster_spec.configurations['global'][
                                 'hregion_memstoreflushsize'])
            ui_handlers[
                'hbase-site/hbase.client.scanner.caching'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/hbase.client.scanner.caching'),
                        "121"),
                    cluster_spec.configurations)
            self.assertEqual("121", cluster_spec.configurations['hbase-site'][
                             'hbase.client.scanner.caching'])
            self.assertEqual("121", cluster_spec.configurations['global'][
                             'client_scannercaching'])
            ui_handlers[
                'hbase-site/zookeeper.session.timeout'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/zookeeper.session.timeout'),
                        "122"),
                    cluster_spec.configurations)
            self.assertEqual("122", cluster_spec.configurations['hbase-site'][
                             'zookeeper.session.timeout'])
            self.assertEqual("122", cluster_spec.configurations['global'][
                             'zookeeper_sessiontimeout'])
            ui_handlers[
                'hbase-site/hbase.client.keyvalue.maxsize'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '',
                            'hbase-site/hbase.client.keyvalue.maxsize'),
                        "123"),
                    cluster_spec.configurations)
            self.assertEqual("123", cluster_spec.configurations['hbase-site'][
                             'hbase.client.keyvalue.maxsize'])
            self.assertEqual("123", cluster_spec.configurations['global'][
                             'hfile_max_keyvalue_size'])
            ui_handlers[
                'hdfs-site/dfs.support.append'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hdfs-site/dfs.support.append'),
                        "false"),
                    cluster_spec.configurations)
            self.assertEqual("false", cluster_spec.configurations['hbase-site']
                             ['dfs.support.append'])
            self.assertEqual("false", cluster_spec.configurations['hdfs-site'][
                             'dfs.support.append'])
            self.assertEqual("false", cluster_spec.configurations['global'][
                             'hdfs_support_append'])
            ui_handlers[
                'hbase-site/dfs.client.read.shortcircuit'](
                    hdp_test_base.TestUserInput(
                        hdp_test_base.TestUserInputConfig(
                            '', '', 'hbase-site/dfs.client.read.shortcircuit'),
                        "false"),
                    cluster_spec.configurations)
            self.assertEqual("false", cluster_spec.configurations['hbase-site']
                             ['dfs.client.read.shortcircuit'])
            self.assertEqual("false", cluster_spec.configurations['global'][
                             'hdfs_enable_shortcircuit_read'])

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_hbase_validation(self, patched):
        master_host = hdp_test_base.TestServer(
            'master.novalocal', 'master', '11111', 3,
            '111.11.1111', '222.11.1111')
        master_ng = hdp_test_base.TestNodeGroup(
            'master', [master_host], ["NAMENODE",
                                      'RESOURCEMANAGER', 'YARN_CLIENT',
                                      'NODEMANAGER',
                                      "SECONDARY_NAMENODE",
                                      "DATANODE",
                                      "AMBARI_SERVER",
                                      'HISTORYSERVER', 'MAPREDUCE2_CLIENT',
                                      'ZOOKEEPER_SERVER', 'ZOOKEEPER_CLIENT'])
        hbase_host = hdp_test_base.TestServer(
            'hbase.novalocal', 'hbase', '11111', 3,
            '111.11.1111', '222.11.1111')

        hbase_ng = hdp_test_base.TestNodeGroup(
            'hbase', [hbase_host], ["HBASE_MASTER"])

        hbase_ng2 = hdp_test_base.TestNodeGroup(
            'hbase2', [hbase_host], ["HBASE_MASTER"])

        hbase_client_host = hdp_test_base.TestServer(
            'hbase-client.novalocal', 'hbase-client', '11111', 3,
            '111.11.1111', '222.11.1111')

        hbase_client_ng = hdp_test_base.TestNodeGroup(
            'hbase-client', [hbase_client_host], ["HBASE_CLIENT"])

        hbase_slave_host = hdp_test_base.TestServer(
            'hbase-rs.novalocal', 'hbase-rs', '11111', 3,
            '111.11.1111', '222.11.1111')

        hbase_slave_ng = hdp_test_base.TestNodeGroup(
            'hbase-rs', [hbase_slave_host], ["HBASE_REGIONSERVER"])

        cluster = hdp_test_base.TestCluster([master_ng, hbase_client_ng])
        cluster_spec = hdp_test_base.create_clusterspec()

        # validation should fail due to lack of hbase master
        self.assertRaises(
            ex.InvalidComponentCountException,
            cluster_spec.create_operational_config, cluster, [])

        cluster = hdp_test_base.TestCluster(
            [master_ng, hbase_client_ng, hbase_slave_ng])
        cluster_spec = hdp_test_base.create_clusterspec()

        # validation should fail due to lack of hbase master

        self.assertRaises(
            ex.InvalidComponentCountException,
            cluster_spec.create_operational_config, cluster, [])

        cluster = hdp_test_base.TestCluster(
            [master_ng, hbase_client_ng, hbase_ng])
        cluster_spec = hdp_test_base.create_clusterspec()

        # validation should succeed with hbase master included
        cluster_spec.create_operational_config(cluster, [])

        cluster = hdp_test_base.TestCluster(
            [master_ng, hbase_client_ng, hbase_ng, hbase_ng2])
        cluster_spec = hdp_test_base.create_clusterspec()

        # validation should fail with multiple hbase master components
        self.assertRaises(
            ex.InvalidComponentCountException,
            cluster_spec.create_operational_config, cluster, [])

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_hdp2_hbase_validation(self, patched):
        master_host = hdp_test_base.TestServer(
            'master.novalocal', 'master', '11111', 3,
            '111.11.1111', '222.11.1111')
        master_ng = hdp_test_base.TestNodeGroup(
            'master', [master_host], ["NAMENODE", "RESOURCEMANAGER",
                                      "SECONDARY_NAMENODE", "HISTORYSERVER",
                                      "NODEMANAGER", "DATANODE",
                                      "AMBARI_SERVER", "ZOOKEEPER_SERVER"])
        hbase_host = hdp_test_base.TestServer(
            'hbase.novalocal', 'hbase', '11111', 3,
            '111.11.1111', '222.11.1111')

        hbase_ng = hdp_test_base.TestNodeGroup(
            'hbase', [hbase_host], ["HBASE_MASTER"])

        hbase_ng2 = hdp_test_base.TestNodeGroup(
            'hbase2', [hbase_host], ["HBASE_MASTER"])

        hbase_client_host = hdp_test_base.TestServer(
            'hbase-client.novalocal', 'hbase-client', '11111', 3,
            '111.11.1111', '222.11.1111')

        hbase_client_ng = hdp_test_base.TestNodeGroup(
            'hbase-client', [hbase_client_host], ["HBASE_CLIENT"])

        hbase_slave_host = hdp_test_base.TestServer(
            'hbase-rs.novalocal', 'hbase-rs', '11111', 3,
            '111.11.1111', '222.11.1111')

        hbase_slave_ng = hdp_test_base.TestNodeGroup(
            'hbase-rs', [hbase_slave_host], ["HBASE_REGIONSERVER"])

        cluster = hdp_test_base.TestCluster([master_ng, hbase_client_ng])
        cluster_spec = hdp_test_base.create_clusterspec(hdp_version='2.0.6')

        # validation should fail due to lack of hbase master
        self.assertRaises(
            ex.InvalidComponentCountException,
            cluster_spec.create_operational_config, cluster, [])

        cluster = hdp_test_base.TestCluster(
            [master_ng, hbase_client_ng, hbase_slave_ng])
        cluster_spec = hdp_test_base.create_clusterspec(hdp_version='2.0.6')

        # validation should fail due to lack of hbase master

        self.assertRaises(
            ex.InvalidComponentCountException,
            cluster_spec.create_operational_config, cluster, [])

        cluster = hdp_test_base.TestCluster(
            [master_ng, hbase_client_ng, hbase_ng])
        cluster_spec = hdp_test_base.create_clusterspec(hdp_version='2.0.6')

        # validation should succeed with hbase master included
        cluster_spec.create_operational_config(cluster, [])

        cluster = hdp_test_base.TestCluster(
            [master_ng, hbase_client_ng, hbase_ng, hbase_ng2])
        cluster_spec = hdp_test_base.create_clusterspec(hdp_version='2.0.6')

        # validation should fail with multiple hbase master components
        self.assertRaises(
            ex.InvalidComponentCountException,
            cluster_spec.create_operational_config, cluster, [])

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_hbase_service_urls(self, patched):
        for version in versions:
            cluster = self._create_hbase_cluster()
            cluster_spec = hdp_test_base.create_clusterspec(
                hdp_version=version)
            cluster_spec.create_operational_config(cluster, [])
            s = self.get_services_processor(version=version)
            service = s.create_service('HBASE')

            url_info = {}
            service.register_service_urls(cluster_spec, url_info, mock.Mock())
            self.assertEqual(1, len(url_info))
            self.assertEqual(6, len(url_info['HBase']))
            self.assertEqual('http://222.22.2222:60010/master-status',
                             url_info['HBase']['Web UI'])
            self.assertEqual('http://222.22.2222:60010/logs',
                             url_info['HBase']['Logs'])
            self.assertEqual('http://222.22.2222:60010/zk.jsp',
                             url_info['HBase']['Zookeeper Info'])
            self.assertEqual('http://222.22.2222:60010/jmx',
                             url_info['HBase']['JMX'])
            self.assertEqual('http://222.22.2222:60010/dump',
                             url_info['HBase']['Debug Dump'])
            self.assertEqual('http://222.22.2222:60010/stacks',
                             url_info['HBase']['Thread Stacks'])

    @mock.patch("sahara.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
        '_get_swift_properties',
        return_value=[])
    def test_hbase_replace_tokens(self, patched):
        for version in versions:
            cluster = self._create_hbase_cluster()
            cluster_spec = hdp_test_base.create_clusterspec(
                hdp_version=version)
            cluster_spec.create_operational_config(cluster, [])
            s = self.get_services_processor(version=version)
            service = s.create_service('HBASE')
            service.finalize_configuration(cluster_spec)

            self.assertEqual("hdfs://master.novalocal:8020/apps/hbase/data",
                             cluster_spec.configurations['hbase-site'][
                                 'hbase.rootdir'])
            self.assertEqual(set(['zk.novalocal', 'master.novalocal']),
                             set(cluster_spec.configurations['hbase-site'][
                                 'hbase.zookeeper.quorum'].split(',')))

    def test_get_storage_paths(self):
        for version in versions:
            s = self.get_services_processor(version=version)
            service = s.create_service('AMBARI')
            server1 = hdp_test_base.TestServer(
                'host1', 'test-master', '11111', 3, '1.1.1.1', '2.2.2.2')
            server2 = hdp_test_base.TestServer(
                'host2', 'test-slave', '11111', 3, '3.3.3.3', '4.4.4.4')
            server3 = hdp_test_base.TestServer(
                'host3', 'another-test', '11111', 3, '6.6.6.6', '5.5.5.5')
            ng1 = hdp_test_base.TestNodeGroup('ng1', [server1], None)
            ng2 = hdp_test_base.TestNodeGroup('ng2', [server2], None)
            ng3 = hdp_test_base.TestNodeGroup('ng3', [server3], None)

            server1.storage_path = ['/volume/disk1']
            server2.storage_path = ['/mnt']

            paths = service._get_common_paths([ng1, ng2])
            self.assertEqual([], paths)

            server1.storage_path = ['/volume/disk1', '/volume/disk2']
            server2.storage_path = ['/mnt']
            server3.storage_path = ['/volume/disk1']

            paths = service._get_common_paths([ng1, ng2, ng3])
            self.assertEqual([], paths)

            server1.storage_path = ['/volume/disk1', '/volume/disk2']
            server2.storage_path = ['/volume/disk1']
            server3.storage_path = ['/volume/disk1']

            paths = service._get_common_paths([ng1, ng2, ng3])
            self.assertEqual(['/volume/disk1'], paths)

    def _create_hbase_cluster(self):
        master_host = hdp_test_base.TestServer(
            'master.novalocal', 'master', '11111', 3,
            '111.11.1111', '222.11.1111')
        master_ng = hdp_test_base.TestNodeGroup(
            'master', [master_host], ["NAMENODE", "RESOURCEMANAGER",
                                      "SECONDARY_NAMENODE", "NODEMANAGER",
                                      "DATANODE", "AMBARI_SERVER",
                                      "HISTORYSERVER", "ZOOKEEPER_SERVER"])
        extra_zk_host = hdp_test_base.TestServer(
            'zk.novalocal', 'zk', '11112', 3,
            '111.11.1112', '222.11.1112')
        extra_zk_ng = hdp_test_base.TestNodeGroup(
            'zk', [extra_zk_host], ['ZOOKEEPER_SERVER'])
        hbase_host = hdp_test_base.TestServer(
            'hbase.novalocal', 'hbase', '11111', 3,
            '222.22.2222', '222.11.1111')
        hbase_ng = hdp_test_base.TestNodeGroup(
            'hbase', [hbase_host], ["HBASE_MASTER"])
        return hdp_test_base.TestCluster([master_ng, extra_zk_ng, hbase_ng])
