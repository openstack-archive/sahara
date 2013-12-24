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

import unittest2

import savanna.plugins.hdp.services as s
from savanna.tests.unit.plugins.hdp import hdp_test_base


class ServicesTest(unittest2.TestCase):
    #TODO(jspeidel): test remaining service functionality which isn't
    # tested by coarser grained unit tests.

    def test_create_hdfs_service(self):
        service = s.create_service('HDFS')
        self.assertEqual('HDFS', service.name)
        expected_configs = set(['global', 'core-site', 'hdfs-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())

    def test_hdfs_service_register_urls(self):
        service = s.create_service('HDFS')
        cluster_spec = mock.Mock()
        cluster_spec.configurations = {
            'core-site': {
                'fs.default.name': 'hdfs://not_expected.com:9020'
            },
            'hdfs-site': {
                'dfs.http.address': 'http://not_expected.com:10070'
            }
        }
        instance_mock = mock.Mock()
        instance_mock.management_ip = '127.0.0.1'
        cluster_spec.determine_component_hosts = mock.Mock(
            return_value=[instance_mock])
        url_info = {}
        url_info = service.register_service_urls(cluster_spec, url_info)
        self.assertEqual(url_info['HDFS']['Web UI'],
                         'http://127.0.0.1:10070')
        self.assertEqual(url_info['HDFS']['NameNode'],
                         'hdfs://127.0.0.1:9020')

    def test_create_mr_service(self):
        service = s.create_service('MAPREDUCE')
        self.assertEqual('MAPREDUCE', service.name)
        expected_configs = set(['global', 'core-site', 'mapred-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())

    def test_mr_service_register_urls(self):
        service = s.create_service('MAPREDUCE')
        cluster_spec = mock.Mock()
        cluster_spec.configurations = {
            'mapred-site': {
                'mapred.job.tracker': 'hdfs://not_expected.com:10300',
                'mapred.job.tracker.http.address':
                'http://not_expected.com:10030'
            }
        }
        instance_mock = mock.Mock()
        instance_mock.management_ip = '127.0.0.1'
        cluster_spec.determine_component_hosts = mock.Mock(
            return_value=[instance_mock])
        url_info = {}
        url_info = service.register_service_urls(cluster_spec, url_info)
        self.assertEqual(url_info['MapReduce']['Web UI'],
                         'http://127.0.0.1:10030')
        self.assertEqual(url_info['MapReduce']['JobTracker'],
                         '127.0.0.1:10300')

    def test_create_hive_service(self):
        service = s.create_service('HIVE')
        self.assertEqual('HIVE', service.name)
        expected_configs = set(['global', 'core-site', 'hive-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_webhcat_service(self):
        service = s.create_service('WEBHCAT')
        self.assertEqual('WEBHCAT', service.name)
        expected_configs = set(['global', 'core-site', 'webhcat-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_zk_service(self):
        service = s.create_service('ZOOKEEPER')
        self.assertEqual('ZOOKEEPER', service.name)
        expected_configs = set(['global', 'core-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_oozie_service(self):
        service = s.create_service('OOZIE')
        self.assertEqual('OOZIE', service.name)
        expected_configs = set(['global', 'core-site', 'oozie-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_oozie_service_register_urls(self):
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
        url_info = service.register_service_urls(cluster_spec, url_info)
        self.assertEqual(url_info['JobFlow']['Oozie'],
                         'http://127.0.0.1:21000')

    def test_create_ganglia_service(self):
        service = s.create_service('GANGLIA')
        self.assertEqual('GANGLIA', service.name)
        expected_configs = set(['global', 'core-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_ambari_service(self):
        service = s.create_service('AMBARI')
        self.assertEqual('AMBARI', service.name)
        expected_configs = set(['global', 'core-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())

    @mock.patch("savanna.utils.openstack.nova.get_instance_info",
                hdp_test_base.get_instance_info)
    @mock.patch(
        'savanna.plugins.hdp.services.HdfsService._get_swift_properties',
        return_value=[])
    def test_create_sqoop_service(self, patched):
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
            'master', [master_host], ["NAMENODE", "JOBTRACKER",
            "SECONDARY_NAMENODE", "TASKTRACKER", "DATANODE", "AMBARI_SERVER"])
        sqoop_host = hdp_test_base.TestServer(
            'sqoop.novalocal', 'sqoop', '11111', 3,
            '111.11.1111', '222.11.1111')
        sqoop_ng = hdp_test_base.TestNodeGroup(
            'sqoop', [sqoop_host], ["SQOOP"])
        cluster = hdp_test_base.TestCluster([master_ng, sqoop_ng])

        cluster_spec = hdp_test_base.create_clusterspec()
        cluster_spec.create_operational_config(cluster, [])

        components = cluster_spec.get_node_groups_containing_component(
            'SQOOP')[0].components
        self.assertIn('HDFS_CLIENT', components)
        self.assertIn('MAPREDUCE_CLIENT', components)

    def test_get_storage_paths(self):
        service = s.create_service('AMBARI')
        ng1 = hdp_test_base.TestNodeGroup(None, None, None)
        ng1.ng_storage_paths = ['/mnt', '/volume/disk1']
        ng2 = hdp_test_base.TestNodeGroup(None, None, None)
        ng2.ng_storage_paths = ['/mnt']

        paths = service._get_common_paths([ng1, ng2])
        self.assertEqual(['/mnt'], paths)

        ng3 = hdp_test_base.TestNodeGroup(None, None, None)
        ng1.ng_storage_paths = ['/mnt', '/volume/disk1', '/volume/disk2']
        ng2.ng_storage_paths = ['/mnt']
        ng3.ng_storage_paths = ['/mnt', '/volume/disk1']

        paths = service._get_common_paths([ng1, ng2, ng3])
        self.assertEqual(['/mnt'], paths)

        ng1.ng_storage_paths = ['/mnt', '/volume/disk1', '/volume/disk2']
        ng2.ng_storage_paths = ['/mnt', '/volume/disk1']
        ng3.ng_storage_paths = ['/mnt', '/volume/disk1']

        paths = service._get_common_paths([ng1, ng2, ng3])
        self.assertEqual(['/volume/disk1'], paths)
