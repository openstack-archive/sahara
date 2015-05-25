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
import pkg_resources as pkg

from sahara.conductor import resource as rsc
from sahara.plugins import exceptions as ex
from sahara.plugins.hdp import clusterspec as cs
from sahara.plugins.hdp.versions.version_2_0_6 import services as s2
from sahara.plugins import provisioning
from sahara.tests.unit import base as sahara_base
import sahara.tests.unit.plugins.hdp.hdp_test_base as base
from sahara.topology import topology_helper as th
from sahara import version


class TestCONF(object):
    def __init__(self, enable_data_locality, enable_hypervisor_awareness):
        self.enable_data_locality = enable_data_locality
        self.enable_hypervisor_awareness = enable_hypervisor_awareness


@mock.patch("sahara.utils.openstack.nova.get_instance_info",
            base.get_instance_info)
@mock.patch('sahara.plugins.hdp.versions.version_2_0_6.services.HdfsService.'
            '_get_swift_properties',
            return_value=[])
class ClusterSpecTestForHDP2(sahara_base.SaharaTestCase):
    service_validators = {}

    def setUp(self):
        super(ClusterSpecTestForHDP2, self).setUp()
        self.service_validators['YARN'] = self._assert_yarn
        self.service_validators['HDFS'] = self._assert_hdfs
        self.service_validators['MAPREDUCE2'] = self._assert_mrv2
        self.service_validators['GANGLIA'] = self._assert_ganglia
        self.service_validators['NAGIOS'] = self._assert_nagios
        self.service_validators['AMBARI'] = self._assert_ambari
        self.service_validators['PIG'] = self._assert_pig
        self.service_validators['HIVE'] = self._assert_hive
        self.service_validators['HCATALOG'] = self._assert_hcatalog
        self.service_validators['ZOOKEEPER'] = self._assert_zookeeper
        self.service_validators['WEBHCAT'] = self._assert_webhcat
        self.service_validators['OOZIE'] = self._assert_oozie
        self.service_validators['SQOOP'] = self._assert_sqoop
        self.service_validators['HBASE'] = self._assert_hbase
        self.service_validators['HUE'] = self._assert_hue

    def test_parse_default_with_cluster(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                  '111.11.1111', '222.11.1111')
        server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                  '222.22.2222', '333.22.2222')

        node_group1 = TestNodeGroup(
            'master', [server1], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "SECONDARY_NAMENODE",
                                  "GANGLIA_SERVER", "GANGLIA_MONITOR",
                                  "NAGIOS_SERVER", "AMBARI_SERVER",
                                  "AMBARI_AGENT", "ZOOKEEPER_SERVER"])
        node_group2 = TestNodeGroup('slave', [server2], ['NODEMANAGER',
                                                         'DATANODE'])
        cluster = base.TestCluster([node_group1, node_group2])

        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [])

        self._assert_services(cluster_config.services)
        self._assert_configurations(cluster_config.configurations)

        node_groups = cluster_config.node_groups
        self.assertEqual(2, len(node_groups))
        self.assertIn('master', node_groups)
        self.assertIn('slave', node_groups)

        master_node_group = node_groups['master']
        self.assertEqual('master', master_node_group.name)
        self.assertEqual(13, len(master_node_group.components))
        self.assertIn('NAMENODE', master_node_group.components)
        self.assertIn('RESOURCEMANAGER', master_node_group.components)
        self.assertIn('HISTORYSERVER', master_node_group.components)
        self.assertIn('SECONDARY_NAMENODE', master_node_group.components)
        self.assertIn('GANGLIA_SERVER', master_node_group.components)
        self.assertIn('GANGLIA_MONITOR', master_node_group.components)
        self.assertIn('NAGIOS_SERVER', master_node_group.components)
        self.assertIn('AMBARI_SERVER', master_node_group.components)
        self.assertIn('AMBARI_AGENT', master_node_group.components)
        self.assertIn('YARN_CLIENT', master_node_group.components)
        self.assertIn('ZOOKEEPER_SERVER', master_node_group.components)

        slave_node_group = node_groups['slave']
        self.assertEqual('slave', slave_node_group.name)
        self.assertIn('NODEMANAGER', slave_node_group.components)

        return cluster_config

    def test_determine_component_hosts(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        server1 = base.TestServer('ambari_machine', 'master', '11111', 3,
                                  '111.11.1111', '222.11.1111')
        server2 = base.TestServer('host2', 'slave', '11111', 3, '222.22.2222',
                                  '333.22.2222')
        server3 = base.TestServer('host3', 'slave', '11111', 3, '222.22.2223',
                                  '333.22.2223')

        node_group1 = TestNodeGroup(
            'master', [server1], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "SECONDARY_NAMENODE",
                                  "GANGLIA_SERVER", "NAGIOS_SERVER",
                                  "AMBARI_SERVER", "ZOOKEEPER_SERVER"])
        node_group2 = TestNodeGroup(
            'slave', [server2], ["DATANODE", "NODEMANAGER",
                                 "HDFS_CLIENT", "MAPREDUCE2_CLIENT"])

        node_group3 = TestNodeGroup(
            'slave2', [server3], ["DATANODE", "NODEMANAGER",
                                  "HDFS_CLIENT", "MAPREDUCE2_CLIENT"])

        cluster = base.TestCluster([node_group1, node_group2, node_group3])

        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [])

        hosts = cluster_config.determine_component_hosts('AMBARI_SERVER')
        self.assertEqual(1, len(hosts))
        self.assertEqual('ambari_machine', hosts.pop().fqdn())

        hosts = cluster_config.determine_component_hosts('DATANODE')
        self.assertEqual(2, len(hosts))
        datanodes = set([server2.fqdn(), server3.fqdn()])
        host_fqdn = set([hosts.pop().fqdn(), hosts.pop().fqdn()])
        # test intersection is both servers
        self.assertEqual(datanodes, host_fqdn & datanodes)

    def test_finalize_configuration(self, patched):
        patched.return_value = [{'name': 'swift.prop1',
                                'value': 'swift_prop_value'},
                                {'name': 'swift.prop2',
                                'value': 'swift_prop_value2'}]
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        master_host = base.TestServer(
            'master.novalocal', 'master', '11111', 3,
            '111.11.1111', '222.11.1111')

        jt_host = base.TestServer(
            'jt_host.novalocal', 'jt', '11111', 3,
            '111.11.2222', '222.11.2222')

        nn_host = base.TestServer(
            'nn_host.novalocal', 'nn', '11111', 3,
            '111.11.3333', '222.11.3333')

        snn_host = base.TestServer(
            'snn_host.novalocal', 'jt', '11111', 3,
            '111.11.4444', '222.11.4444')

        hive_host = base.TestServer(
            'hive_host.novalocal', 'hive', '11111', 3,
            '111.11.5555', '222.11.5555')

        hive_ms_host = base.TestServer(
            'hive_ms_host.novalocal', 'hive_ms', '11111', 3,
            '111.11.6666', '222.11.6666')

        hive_mysql_host = base.TestServer(
            'hive_mysql_host.novalocal', 'hive_mysql', '11111', 3,
            '111.11.7777', '222.11.7777')

        hcat_host = base.TestServer(
            'hcat_host.novalocal', 'hcat', '11111', 3,
            '111.11.8888', '222.11.8888')

        zk1_host = base.TestServer(
            'zk1_host.novalocal', 'zk1', '11111', 3,
            '111.11.9999', '222.11.9999')

        zk2_host = base.TestServer(
            'zk2_host.novalocal', 'zk2', '11112', 3,
            '111.11.9990', '222.11.9990')

        oozie_host = base.TestServer(
            'oozie_host.novalocal', 'oozie', '11111', 3,
            '111.11.9999', '222.11.9999')

        slave_host = base.TestServer(
            'slave1.novalocal', 'slave', '11111', 3,
            '222.22.6666', '333.22.6666')

        master_ng = TestNodeGroup(
            'master', [master_host], ["GANGLIA_SERVER",
                                      "GANGLIA_MONITOR",
                                      "NAGIOIS_SERVER",
                                      "AMBARI_SERVER",
                                      "AMBARI_AGENT"])

        jt_ng = TestNodeGroup(
            'jt', [jt_host], ["RESOURCEMANAGER", "GANGLIA_MONITOR",
                              "HISTORYSERVER", "AMBARI_AGENT"])

        nn_ng = TestNodeGroup(
            'nn', [nn_host], ["NAMENODE", "GANGLIA_MONITOR",
                              "AMBARI_AGENT"])

        snn_ng = TestNodeGroup(
            'snn', [snn_host], ["SECONDARY_NAMENODE", "GANGLIA_MONITOR",
                                "AMBARI_AGENT"])

        hive_ng = TestNodeGroup(
            'hive', [hive_host], ["HIVE_SERVER", "GANGLIA_MONITOR",
                                  "AMBARI_AGENT"])

        hive_ms_ng = TestNodeGroup(
            'meta', [hive_ms_host], ["HIVE_METASTORE", "GANGLIA_MONITOR",
                                     "AMBARI_AGENT"])

        hive_mysql_ng = TestNodeGroup(
            'mysql', [hive_mysql_host], ["MYSQL_SERVER", "GANGLIA_MONITOR",
                                         "AMBARI_AGENT"])

        hcat_ng = TestNodeGroup(
            'hcat', [hcat_host], ["WEBHCAT_SERVER", "GANGLIA_MONITOR",
                                  "AMBARI_AGENT"])

        zk1_ng = TestNodeGroup(
            'zk1', [zk1_host], ["ZOOKEEPER_SERVER", "GANGLIA_MONITOR",
                                "AMBARI_AGENT"])

        zk2_ng = TestNodeGroup(
            'zk2', [zk2_host], ["ZOOKEEPER_SERVER", "GANGLIA_MONITOR",
                                "AMBARI_AGENT"])

        oozie_ng = TestNodeGroup(
            'oozie', [oozie_host], ["OOZIE_SERVER", "GANGLIA_MONITOR",
                                    "AMBARI_AGENT"])
        slave_ng = TestNodeGroup(
            'slave', [slave_host], ["DATANODE", "NODEMANAGER",
                                    "GANGLIA_MONITOR", "HDFS_CLIENT",
                                    "MAPREDUCE2_CLIENT", "OOZIE_CLIENT",
                                    "AMBARI_AGENT"])

        user_input_config = TestUserInputConfig(
            'core-site', 'cluster', 'fs.defaultFS')
        user_input = provisioning.UserInput(
            user_input_config, 'hdfs://nn_dif_host.novalocal:8020')

        cluster = base.TestCluster([master_ng, jt_ng, nn_ng, snn_ng, hive_ng,
                                    hive_ms_ng, hive_mysql_ng,
                                    hcat_ng, zk1_ng, zk2_ng, oozie_ng,
                                    slave_ng])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [user_input])
        config = cluster_config.configurations

        # for this value, validating that user inputs override configured
        # values, whether they are processed by runtime or not
        self.assertEqual('hdfs://nn_dif_host.novalocal:8020',
                         config['core-site']['fs.defaultFS'])

        self.assertEqual('jt_host.novalocal:19888',
                         config['mapred-site']
                         ['mapreduce.jobhistory.webapp.address'])

        self.assertEqual('nn_host.novalocal:50070',
                         config['hdfs-site']['dfs.namenode.http-address'])
        self.assertEqual('snn_host.novalocal:50090',
                         config['hdfs-site']
                         ['dfs.namenode.secondary.http-address'])
        self.assertEqual('nn_host.novalocal:50470',
                         config['hdfs-site']['dfs.namenode.https-address'])

        self.assertEqual('hive_host.novalocal',
                         config['global']['hive_hostname'])
        self.assertEqual('hive_host.novalocal',
                         config['core-site']['hadoop.proxyuser.hive.hosts'])
        self.assertEqual('jdbc:mysql://hive_mysql_host.novalocal/hive?'
                         'createDatabaseIfNotExist=true',
                         config['hive-site']
                         ['javax.jdo.option.ConnectionURL'])
        self.assertEqual('thrift://hive_ms_host.novalocal:9083',
                         config['hive-site']['hive.metastore.uris'])
        self.assertTrue(
            'hive.metastore.uris=thrift://hive_ms_host.novalocal:9083' in
            config['webhcat-site']['templeton.hive.properties'])
        self.assertEqual('hcat_host.novalocal',
                         config['core-site']['hadoop.proxyuser.hcat.hosts'])
        self.assertEqual(
            set(['zk1_host.novalocal:2181', 'zk2_host.novalocal:2181']),
            set(config['webhcat-site']
                ['templeton.zookeeper.hosts'].split(',')))

        self.assertEqual('http://oozie_host.novalocal:11000/oozie',
                         config['oozie-site']['oozie.base.url'])
        self.assertEqual('oozie_host.novalocal',
                         config['global']['oozie_hostname'])
        self.assertEqual('oozie_host.novalocal,222.11.9999,111.11.9999',
                         config['core-site']['hadoop.proxyuser.oozie.hosts'])

        # test swift properties
        self.assertEqual('swift_prop_value',
                         config['core-site']['swift.prop1'])
        self.assertEqual('swift_prop_value2',
                         config['core-site']['swift.prop2'])

    def test_finalize_configuration_with_hue(self, patched):
        patched.return_value = [{'name': 'swift.prop1',
                                'value': 'swift_prop_value'},
                                {'name': 'swift.prop2',
                                'value': 'swift_prop_value2'}]
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        master_host = base.TestServer(
            'master.novalocal', 'master', '11111', 3,
            '111.11.1111', '222.11.1111')

        jt_host = base.TestServer(
            'jt_host.novalocal', 'jt', '11111', 3,
            '111.11.2222', '222.11.2222')

        nn_host = base.TestServer(
            'nn_host.novalocal', 'nn', '11111', 3,
            '111.11.3333', '222.11.3333')

        snn_host = base.TestServer(
            'snn_host.novalocal', 'jt', '11111', 3,
            '111.11.4444', '222.11.4444')

        hive_host = base.TestServer(
            'hive_host.novalocal', 'hive', '11111', 3,
            '111.11.5555', '222.11.5555')

        hive_ms_host = base.TestServer(
            'hive_ms_host.novalocal', 'hive_ms', '11111', 3,
            '111.11.6666', '222.11.6666')

        hive_mysql_host = base.TestServer(
            'hive_mysql_host.novalocal', 'hive_mysql', '11111', 3,
            '111.11.7777', '222.11.7777')

        hcat_host = base.TestServer(
            'hcat_host.novalocal', 'hcat', '11111', 3,
            '111.11.8888', '222.11.8888')

        zk1_host = base.TestServer(
            'zk1_host.novalocal', 'zk1', '11111', 3,
            '111.11.9999', '222.11.9999')

        zk2_host = base.TestServer(
            'zk2_host.novalocal', 'zk2', '11112', 3,
            '111.11.9990', '222.11.9990')

        oozie_host = base.TestServer(
            'oozie_host.novalocal', 'oozie', '11111', 3,
            '111.11.9999', '222.11.9999')

        slave_host = base.TestServer(
            'slave1.novalocal', 'slave', '11111', 3,
            '222.22.6666', '333.22.6666')

        master_ng = TestNodeGroup(
            'master', [master_host], ["GANGLIA_SERVER",
                                      "GANGLIA_MONITOR",
                                      "NAGIOIS_SERVER",
                                      "AMBARI_SERVER",
                                      "AMBARI_AGENT"])

        jt_ng = TestNodeGroup(
            'jt', [jt_host], ["RESOURCEMANAGER", "GANGLIA_MONITOR",
                              "HISTORYSERVER", "AMBARI_AGENT"])

        nn_ng = TestNodeGroup(
            'nn', [nn_host], ["NAMENODE", "GANGLIA_MONITOR",
                              "AMBARI_AGENT"])

        snn_ng = TestNodeGroup(
            'snn', [snn_host], ["SECONDARY_NAMENODE", "GANGLIA_MONITOR",
                                "AMBARI_AGENT"])

        hive_ng = TestNodeGroup(
            'hive', [hive_host], ["HIVE_SERVER", "GANGLIA_MONITOR",
                                  "AMBARI_AGENT"])

        hive_ms_ng = TestNodeGroup(
            'meta', [hive_ms_host], ["HIVE_METASTORE", "GANGLIA_MONITOR",
                                     "AMBARI_AGENT"])

        hive_mysql_ng = TestNodeGroup(
            'mysql', [hive_mysql_host], ["MYSQL_SERVER", "GANGLIA_MONITOR",
                                         "AMBARI_AGENT"])

        hcat_ng = TestNodeGroup(
            'hcat', [hcat_host], ["WEBHCAT_SERVER", "GANGLIA_MONITOR",
                                  "AMBARI_AGENT"])

        zk1_ng = TestNodeGroup(
            'zk1', [zk1_host], ["ZOOKEEPER_SERVER", "GANGLIA_MONITOR",
                                "AMBARI_AGENT"])

        zk2_ng = TestNodeGroup(
            'zk2', [zk2_host], ["ZOOKEEPER_SERVER", "GANGLIA_MONITOR",
                                "AMBARI_AGENT"])

        oozie_ng = TestNodeGroup(
            'oozie', [oozie_host], ["OOZIE_SERVER", "GANGLIA_MONITOR",
                                    "AMBARI_AGENT"])
        slave_ng = TestNodeGroup(
            'slave', [slave_host], ["DATANODE", "NODEMANAGER",
                                    "GANGLIA_MONITOR", "HDFS_CLIENT",
                                    "MAPREDUCE2_CLIENT", "OOZIE_CLIENT",
                                    "AMBARI_AGENT", "HUE"])

        user_input_config = TestUserInputConfig(
            'core-site', 'cluster', 'fs.defaultFS')
        user_input = provisioning.UserInput(
            user_input_config, 'hdfs://nn_dif_host.novalocal:8020')

        cluster = base.TestCluster([master_ng, jt_ng, nn_ng, snn_ng, hive_ng,
                                    hive_ms_ng, hive_mysql_ng,
                                    hcat_ng, zk1_ng, zk2_ng, oozie_ng,
                                    slave_ng])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [user_input])
        config = cluster_config.configurations

        # for this value, validating that user inputs override configured
        # values, whether they are processed by runtime or not
        self.assertEqual('hdfs://nn_dif_host.novalocal:8020',
                         config['core-site']['fs.defaultFS'])

        self.assertEqual('jt_host.novalocal:19888',
                         config['mapred-site']
                         ['mapreduce.jobhistory.webapp.address'])

        self.assertEqual('nn_host.novalocal:50070',
                         config['hdfs-site']['dfs.namenode.http-address'])
        self.assertEqual('snn_host.novalocal:50090',
                         config['hdfs-site']
                         ['dfs.namenode.secondary.http-address'])
        self.assertEqual('nn_host.novalocal:50470',
                         config['hdfs-site']['dfs.namenode.https-address'])
        self.assertEqual('true',
                         config['hdfs-site']['dfs.support.broken.append'])
        self.assertEqual('true',
                         config['hdfs-site']['dfs.webhdfs.enabled'])

        self.assertEqual('hive_host.novalocal',
                         config['global']['hive_hostname'])
        self.assertEqual('hive_host.novalocal',
                         config['core-site']['hadoop.proxyuser.hive.hosts'])
        self.assertEqual('jdbc:mysql://hive_mysql_host.novalocal/hive?'
                         'createDatabaseIfNotExist=true',
                         config['hive-site']
                         ['javax.jdo.option.ConnectionURL'])
        self.assertEqual('thrift://hive_ms_host.novalocal:9083',
                         config['hive-site']['hive.metastore.uris'])
        self.assertTrue(
            'hive.metastore.uris=thrift://hive_ms_host.novalocal:9083' in
            config['webhcat-site']['templeton.hive.properties'])
        self.assertEqual('*',
                         config['core-site']['hadoop.proxyuser.hcat.hosts'])
        self.assertEqual('*',
                         config['core-site']['hadoop.proxyuser.hcat.groups'])
        self.assertEqual('*',
                         config['core-site']['hadoop.proxyuser.hue.hosts'])
        self.assertEqual('*',
                         config['core-site']['hadoop.proxyuser.hue.groups'])
        self.assertEqual(
            set(['zk1_host.novalocal:2181', 'zk2_host.novalocal:2181']),
            set(config['webhcat-site']
                ['templeton.zookeeper.hosts'].split(',')))
        self.assertEqual('*',
                         config['webhcat-site']['webhcat.proxyuser.hue.hosts'])
        self.assertEqual('*',
                         config['webhcat-site']
                         ['webhcat.proxyuser.hue.groups'])

        self.assertEqual('http://oozie_host.novalocal:11000/oozie',
                         config['oozie-site']['oozie.base.url'])
        self.assertEqual('*',
                         config['oozie-site']
                         ['oozie.service.ProxyUserService.proxyuser.hue.'
                          'groups'])
        self.assertEqual('*',
                         config['oozie-site']
                         ['oozie.service.ProxyUserService.proxyuser.hue.'
                          'hosts'])
        self.assertEqual('oozie_host.novalocal',
                         config['global']['oozie_hostname'])
        self.assertEqual('oozie_host.novalocal,222.11.9999,111.11.9999',
                         config['core-site']['hadoop.proxyuser.oozie.hosts'])

        # test swift properties
        self.assertEqual('swift_prop_value',
                         config['core-site']['swift.prop1'])
        self.assertEqual('swift_prop_value2',
                         config['core-site']['swift.prop2'])

    def test__determine_deployed_services(self, nova_mock):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        master_host = base.TestServer(
            'master.novalocal', 'master', '11111', 3,
            '111.11.1111', '222.11.1111')

        jt_host = base.TestServer(
            'jt_host.novalocal', 'jt', '11111', 3,
            '111.11.2222', '222.11.2222')

        nn_host = base.TestServer(
            'nn_host.novalocal', 'nn', '11111', 3,
            '111.11.3333', '222.11.3333')

        snn_host = base.TestServer(
            'snn_host.novalocal', 'jt', '11111', 3,
            '111.11.4444', '222.11.4444')

        slave_host = base.TestServer(
            'slave1.novalocal', 'slave', '11111', 3,
            '222.22.6666', '333.22.6666')

        master_ng = TestNodeGroup(
            'master', [master_host],
            ['GANGLIA_SERVER',
             'GANGLIA_MONITOR', 'NAGIOS_SERVER',
             'AMBARI_SERVER', 'AMBARI_AGENT', 'ZOOKEEPER_SERVER'])
        jt_ng = TestNodeGroup('jt', [jt_host], ["RESOURCEMANAGER",
                                                "HISTORYSERVER",
                                                "GANGLIA_MONITOR",
                                                "AMBARI_AGENT"])
        nn_ng = TestNodeGroup('nn', [nn_host], ["NAMENODE",
                              "GANGLIA_MONITOR", "AMBARI_AGENT"])
        snn_ng = TestNodeGroup('snn', [snn_host], ["SECONDARY_NAMENODE",
                               "GANGLIA_MONITOR", "AMBARI_AGENT"])
        slave_ng = TestNodeGroup(
            'slave', [slave_host],
            ["DATANODE", "NODEMANAGER",
             "GANGLIA_MONITOR", "HDFS_CLIENT", "MAPREDUCE2_CLIENT",
             "AMBARI_AGENT"])

        cluster = base.TestCluster([master_ng, jt_ng, nn_ng,
                                   snn_ng, slave_ng])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [])
        services = cluster_config.services
        for service in services:
            if service.name in ['YARN', 'HDFS', 'MAPREDUCE2', 'GANGLIA',
                                'AMBARI', 'NAGIOS', 'ZOOKEEPER']:
                self.assertTrue(service.deployed)
            else:
                self.assertFalse(service.deployed)

    def test_ambari_rpm_path(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')
        cluster_spec = cs.ClusterSpec(cluster_config_file, version='2.0.6')

        ambari_config = cluster_spec.configurations['ambari']
        rpm = ambari_config.get('rpm', None)
        self.assertEqual('http://s3.amazonaws.com/'
                         'public-repo-1.hortonworks.com/ambari/centos6/'
                         '1.x/updates/1.6.0/ambari.repo', rpm)

    def test_fs_umask(self, patched):
        s_conf = s2.CONF
        try:
            s2.CONF = TestCONF(False, False)
            cluster_config_file = pkg.resource_string(
                version.version_info.package,
                'plugins/hdp/versions/version_2_0_6/resources/'
                'default-cluster.template')

            server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                      '111.11.1111', '222.11.1111')
            server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                      '222.22.2222', '333.22.2222')

            node_group1 = TestNodeGroup(
                'master', [server1], ["NAMENODE", "RESOURCEMANAGER",
                                      "SECONDARY_NAMENODE", "GANGLIA_SERVER",
                                      "GANGLIA_MONITOR", "NAGIOS_SERVER",
                                      "AMBARI_SERVER", "AMBARI_AGENT",
                                      "HISTORYSERVER", "ZOOKEEPER_SERVER"])
            node_group2 = TestNodeGroup(
                'slave', [server2], ["NODEMANAGER", "DATANODE", "AMBARI_AGENT",
                                     "GANGLIA_MONITOR"])

            cluster = base.TestCluster([node_group1, node_group2])
            cluster_config = cs.ClusterSpec(cluster_config_file, '2.0.6')
            cluster_config.create_operational_config(cluster, [])
            # core-site
            self.assertEqual(
                '022',
                cluster_config.configurations['hdfs-site']
                ['fs.permissions.umask-mode'])
        finally:
            s2.CONF = s_conf

    def test_parse_default(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')

        self._assert_services(cluster_config.services)
        self._assert_configurations(cluster_config.configurations)

        node_groups = cluster_config.node_groups
        self.assertEqual(2, len(node_groups))
        master_node_group = node_groups['MASTER']
        self.assertEqual('MASTER', master_node_group.name)
        self.assertIsNone(master_node_group.predicate)
        self.assertEqual('1', master_node_group.cardinality)
        self.assertEqual(8, len(master_node_group.components))
        self.assertIn('NAMENODE', master_node_group.components)
        self.assertIn('RESOURCEMANAGER', master_node_group.components)
        self.assertIn('HISTORYSERVER', master_node_group.components)
        self.assertIn('SECONDARY_NAMENODE', master_node_group.components)
        self.assertIn('GANGLIA_SERVER', master_node_group.components)
        self.assertIn('NAGIOS_SERVER', master_node_group.components)
        self.assertIn('AMBARI_SERVER', master_node_group.components)
        self.assertIn('ZOOKEEPER_SERVER', master_node_group.components)

        slave_node_group = node_groups['SLAVE']
        self.assertEqual('SLAVE', slave_node_group.name)
        self.assertIsNone(slave_node_group.predicate)
        self.assertEqual('1+', slave_node_group.cardinality)
        self.assertEqual(5, len(slave_node_group.components))
        self.assertIn('DATANODE', slave_node_group.components)
        self.assertIn('NODEMANAGER', slave_node_group.components)
        self.assertIn('HDFS_CLIENT', slave_node_group.components)
        self.assertIn('YARN_CLIENT', slave_node_group.components)
        self.assertIn('MAPREDUCE2_CLIENT', slave_node_group.components)

        return cluster_config

    def test_ambari_rpm(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')

        self._assert_configurations(cluster_config.configurations)
        ambari_config = cluster_config.configurations['ambari']
        self.assertIsNotNone('no rpm uri found',
                             ambari_config.get('rpm', None))

    def test_normalize(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster = cluster_config.normalize()

        configs = cluster.cluster_configs
        contains_dfs_datanode_http_address = False
        contains_staging_dir = False
        contains_mapred_user = False

        for entry in configs:
            config = entry.config
            # assert some random configurations across targets
            if config.name == 'dfs.datanode.http.address':
                contains_dfs_datanode_http_address = True
                self.assertEqual('string', config.type)
                self.assertEqual('0.0.0.0:50075', config.default_value)
                self.assertEqual('HDFS', config.applicable_target)

            if config.name == 'yarn.app.mapreduce.am.staging-dir':
                contains_staging_dir = True
                self.assertEqual('string', config.type)
                self.assertEqual(
                    '/user',
                    config.default_value)
                self.assertEqual('MAPREDUCE2',
                                 config.applicable_target)

            if config.name == 'mapred_user':
                contains_mapred_user = True
                self.assertEqual('string', config.type)
                self.assertEqual('mapred', config.default_value)
                self.assertEqual('MAPREDUCE2', config.applicable_target)

                #            print 'Config: name: {0}, type:{1},
                # default value:{2}, target:{3}, Value:{4}'.format(
                #                config.name, config.type,
                # config.default_value,
                #  config.applicable_target, entry.value)

        self.assertTrue(contains_dfs_datanode_http_address)
        self.assertTrue(contains_staging_dir)
        self.assertTrue(contains_mapred_user)
        node_groups = cluster.node_groups
        self.assertEqual(2, len(node_groups))
        contains_master_group = False
        contains_slave_group = False
        for i in range(2):
            node_group = node_groups[i]
            components = node_group.node_processes
            if node_group.name == "MASTER":
                contains_master_group = True
                self.assertEqual(8, len(components))
                self.assertIn('NAMENODE', components)
                self.assertIn('RESOURCEMANAGER', components)
                self.assertIn('HISTORYSERVER', components)
                self.assertIn('SECONDARY_NAMENODE', components)
                self.assertIn('GANGLIA_SERVER', components)
                self.assertIn('NAGIOS_SERVER', components)
                self.assertIn('AMBARI_SERVER', components)
                self.assertIn('ZOOKEEPER_SERVER', components)
                # TODO(jspeidel): node configs
                # TODO(jspeidel): vm_requirements
            elif node_group.name == 'SLAVE':
                contains_slave_group = True
                self.assertEqual(5, len(components))
                self.assertIn('DATANODE', components)
                self.assertIn('NODEMANAGER', components)
                self.assertIn('HDFS_CLIENT', components)
                self.assertIn('YARN_CLIENT', components)
                self.assertIn('MAPREDUCE2_CLIENT', components)
                # TODO(jspeidel): node configs
                # TODO(jspeidel): vm requirements
            else:
                self.fail('Unexpected node group: {0}'.format(node_group.name))
        self.assertTrue(contains_master_group)
        self.assertTrue(contains_slave_group)

    def test_existing_config_item_in_top_level_within_blueprint(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        user_input_config = TestUserInputConfig(
            'global', 'OOZIE', 'oozie_log_dir')
        user_input = provisioning.UserInput(user_input_config,
                                            '/some/new/path')

        server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                  '111.11.1111', '222.11.1111')
        server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                  '222.22.2222', '333.22.2222')

        node_group1 = TestNodeGroup(
            'master', [server1], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "SECONDARY_NAMENODE",
                                  "GANGLIA_SERVER", "GANGLIA_MONITOR",
                                  "NAGIOS_SERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER", "AMBARI_AGENT"])
        node_group2 = TestNodeGroup(
            'slave', [server2], ["NODEMANAGER", "DATANODE",
                                 "AMBARI_AGENT", "GANGLIA_MONITOR"])

        cluster = base.TestCluster([node_group1, node_group2])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [user_input])
        self.assertEqual('/some/new/path', cluster_config.configurations
                         ['global']['oozie_log_dir'])

    def test_new_config_item_in_top_level_within_blueprint(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        user_input_config = TestUserInputConfig(
            'global', 'general', 'new_property')
        user_input = provisioning.UserInput(user_input_config, 'foo')

        server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                  '111.11.1111', '222.11.1111')
        server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                  '222.22.2222', '333.22.2222')

        node_group1 = TestNodeGroup(
            'master', [server1],
            ["NAMENODE", "RESOURCEMANAGER",
             "HISTORYSERVER", "SECONDARY_NAMENODE", "GANGLIA_SERVER",
             "GANGLIA_MONITOR", "NAGIOS_SERVER", "AMBARI_SERVER",
             "ZOOKEEPER_SERVER", "AMBARI_AGENT"])
        node_group2 = TestNodeGroup(
            'slave', [server2], ["NODEMANAGER", "DATANODE", "AMBARI_AGENT",
                                 "GANGLIA_MONITOR"])

        cluster = base.TestCluster([node_group1, node_group2])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [user_input])
        self.assertEqual(
            'foo', cluster_config.configurations['global']['new_property'])

    def test_topology_configuration_no_hypervisor(self, patched):
        s_conf = s2.CONF
        th_conf = th.CONF
        try:
            s2.CONF = TestCONF(True, False)
            th.CONF = TestCONF(True, False)
            cluster_config_file = pkg.resource_string(
                version.version_info.package,
                'plugins/hdp/versions/version_2_0_6/resources/'
                'default-cluster.template')

            server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                      '111.11.1111', '222.11.1111')
            server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                      '222.22.2222', '333.22.2222')

            node_group1 = TestNodeGroup(
                'master', [server1], ["NAMENODE", "RESOURCEMANAGER",
                                      "HISTORYSERVER", "SECONDARY_NAMENODE",
                                      "GANGLIA_SERVER", "GANGLIA_MONITOR",
                                      "NAGIOS_SERVER", "AMBARI_SERVER",
                                      "ZOOKEEPER_SERVER", "AMBARI_AGENT"])
            node_group2 = TestNodeGroup(
                'slave', [server2], ["NODEMANAGER", "DATANODE", "AMBARI_AGENT",
                                     "GANGLIA_MONITOR"])

            cluster = base.TestCluster([node_group1, node_group2])
            cluster_config = cs.ClusterSpec(cluster_config_file,
                                            version='2.0.6')
            cluster_config.create_operational_config(cluster, [])
            # core-site
            self.assertEqual(
                'org.apache.hadoop.net.NetworkTopology',
                cluster_config.configurations['core-site']
                ['net.topology.impl'])
            self.assertEqual(
                'true',
                cluster_config.configurations['core-site']
                ['net.topology.nodegroup.aware'])
            self.assertEqual(
                'org.apache.hadoop.hdfs.server.namenode.'
                'BlockPlacementPolicyWithNodeGroup',
                cluster_config.configurations['core-site']
                ['dfs.block.replicator.classname'])
            self.assertEqual(
                'true',
                cluster_config.configurations['core-site']
                ['fs.swift.service.sahara.location-aware'])
            self.assertEqual(
                'org.apache.hadoop.net.ScriptBasedMapping',
                cluster_config.configurations['core-site']
                ['net.topology.node.switch.mapping.impl'])
            self.assertEqual(
                '/etc/hadoop/conf/topology.sh',
                cluster_config.configurations['core-site']
                ['net.topology.script.file.name'])

            # mapred-site
            self.assertEqual(
                'true',
                cluster_config.configurations['mapred-site']
                ['mapred.jobtracker.nodegroup.aware'])
            self.assertEqual(
                '3',
                cluster_config.configurations['mapred-site']
                ['mapred.task.cache.levels'])
            self.assertEqual(
                'org.apache.hadoop.mapred.JobSchedulableWithNodeGroup',
                cluster_config.configurations['mapred-site']
                ['mapred.jobtracker.jobSchedulable'])
        finally:
            s2.CONF = s_conf
            th.CONF = th_conf

    def test_topology_configuration_with_hypervisor(self, patched):
        s_conf = s2.CONF
        try:
            s2.CONF = TestCONF(True, True)
            cluster_config_file = pkg.resource_string(
                version.version_info.package,
                'plugins/hdp/versions/version_2_0_6/resources/'
                'default-cluster.template')

            server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                      '111.11.1111', '222.11.1111')
            server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                      '222.22.2222', '333.22.2222')

            node_group1 = TestNodeGroup(
                'master', [server1], ["NAMENODE", "RESOURCEMANAGER",
                                      "HISTORYSERVER", "SECONDARY_NAMENODE",
                                      "GANGLIA_SERVER", "GANGLIA_MONITOR",
                                      "NAGIOS_SERVER", "AMBARI_SERVER",
                                      "ZOOKEEPER_SERVER", "AMBARI_AGENT"])
            node_group2 = TestNodeGroup(
                'slave', [server2], ["NODEMANAGER", "DATANODE", "AMBARI_AGENT",
                                     "GANGLIA_MONITOR"])

            cluster = base.TestCluster([node_group1, node_group2])
            cluster_config = cs.ClusterSpec(cluster_config_file,
                                            version='2.0.6')
            cluster_config.create_operational_config(cluster, [])
            # core-site
            self.assertEqual(
                'org.apache.hadoop.net.NetworkTopologyWithNodeGroup',
                cluster_config.configurations['core-site']
                ['net.topology.impl'])
        finally:
            s2.CONF = s_conf

    def test_update_ambari_admin_user(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        user_input_config = TestUserInputConfig('ambari-stack', 'AMBARI',
                                                'ambari.admin.user')
        user_input = provisioning.UserInput(user_input_config, 'new-user')

        server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                  '111.11.1111', '222.11.1111')
        server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                  '222.22.2222', '333.22.2222')

        node_group1 = TestNodeGroup(
            'master',
            [server1],
            ["NAMENODE",
             "RESOURCEMANAGER",
             "HISTORYSERVER",
             "SECONDARY_NAMENODE",
             "GANGLIA_SERVER",
             "GANGLIA_MONITOR",
             "NAGIOS_SERVER",
             "AMBARI_SERVER",
             "ZOOKEEPER_SERVER",
             "AMBARI_AGENT"])
        node_group2 = TestNodeGroup(
            'slave',
            [server2],
            ["NODEMANAGER",
             "DATANODE",
             "AMBARI_AGENT",
             "GANGLIA_MONITOR"])

        cluster = base.TestCluster([node_group1, node_group2])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [user_input])
        ambari_service = next(service for service in cluster_config.services
                              if service.name == 'AMBARI')
        users = ambari_service.users
        self.assertEqual(1, len(users))
        self.assertEqual('new-user', users[0].name)

    def test_update_ambari_admin_password(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        user_input_config = TestUserInputConfig('ambari-stack', 'AMBARI',
                                                'ambari.admin.password')
        user_input = provisioning.UserInput(user_input_config, 'new-pwd')

        server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                  '111.11.1111', '222.11.1111')
        server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                  '222.22.2222', '333.22.2222')

        node_group1 = TestNodeGroup(
            'master',
            [server1],
            ["NAMENODE",
             "RESOURCEMANAGER",
             "HISTORYSERVER",
             "SECONDARY_NAMENODE",
             "GANGLIA_SERVER",
             "GANGLIA_MONITOR",
             "NAGIOS_SERVER",
             "AMBARI_SERVER",
             "ZOOKEEPER_SERVER",
             "AMBARI_AGENT"])
        node_group2 = TestNodeGroup(
            'slave',
            [server2],
            ["NODEMANAGER",
             "DATANODE",
             "AMBARI_AGENT",
             "GANGLIA_MONITOR"])

        cluster = base.TestCluster([node_group1, node_group2])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(cluster, [user_input])
        ambari_service = next(service for service in cluster_config.services
                              if service.name == 'AMBARI')
        users = ambari_service.users
        self.assertEqual(1, len(users))
        self.assertEqual('new-pwd', users[0].password)

    def test_update_ambari_admin_user_and_password(self, patched):
        cluster_config_file = pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

        user_user_input_config = TestUserInputConfig('ambari-stack', 'AMBARI',
                                                     'ambari.admin.user')
        pwd_user_input_config = TestUserInputConfig('ambari-stack', 'AMBARI',
                                                    'ambari.admin.password')
        user_user_input = provisioning.UserInput(user_user_input_config,
                                                 'new-admin_user')
        pwd_user_input = provisioning.UserInput(pwd_user_input_config,
                                                'new-admin_pwd')

        server1 = base.TestServer('host1', 'test-master', '11111', 3,
                                  '111.11.1111', '222.11.1111')
        server2 = base.TestServer('host2', 'test-slave', '11111', 3,
                                  '222.22.2222', '333.22.2222')

        node_group1 = TestNodeGroup(
            'one', [server1], ["NAMENODE", "RESOURCEMANAGER",
                               "HISTORYSERVER", "SECONDARY_NAMENODE",
                               "GANGLIA_SERVER", "GANGLIA_MONITOR",
                               "NAGIOS_SERVER", "AMBARI_SERVER",
                               "ZOOKEEPER_SERVER", "AMBARI_AGENT"])
        node_group2 = TestNodeGroup(
            'two', [server2], ["NODEMANAGER", "DATANODE",
                               "AMBARI_AGENT", "GANGLIA_MONITOR"])

        cluster = base.TestCluster([node_group1, node_group2])
        cluster_config = cs.ClusterSpec(cluster_config_file, version='2.0.6')
        cluster_config.create_operational_config(
            cluster, [user_user_input, pwd_user_input])
        ambari_service = next(service for service in cluster_config.services
                              if service.name == 'AMBARI')
        users = ambari_service.users
        self.assertEqual(1, len(users))
        self.assertEqual('new-admin_user', users[0].name)
        self.assertEqual('new-admin_pwd', users[0].password)

    def test_validate_missing_hdfs(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["NODEMANAGER", "MAPREDUCE2_CLIENT",
                                "HISTORYSERVER"])

        node_group2 = TestNodeGroup(
            'master', [server2], ["RESOURCEMANAGER", "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing hdfs service
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.RequiredServiceMissingException:
            # expected
            pass

    def test_validate_missing_mr2(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE"])

        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing mr service
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.RequiredServiceMissingException:
            # expected
            pass

    def test_validate_missing_ambari(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["NAMENODE", "RESOURCEMANAGER",
                                "ZOOKEEPER_SERVER"])

        node_group2 = TestNodeGroup(
            'master', [server2], ["DATANODE", "NODEMANAGER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing ambari service
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.RequiredServiceMissingException:
            # expected
            pass

    # TODO(jspeidel): move validate_* to test_services when validate
    # is called independently of cluspterspec
    def test_validate_hdfs(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "HDFS_CLIENT", "MAPREDUCE2_CLIENT"], 1)

        node_group2 = TestNodeGroup(
            'master', [server2], ["RESOURCEMANAGER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing NN
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "ZOOKEEPER_SERVER",
                                  "AMBARI_SERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should cause validation exception due to 2 NN
        node_group3 = TestNodeGroup(
            'master2', [server2], ["NAMENODE"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

    def test_validate_hdfs_ha(self, patched):
        server1 = base.TestServer('host1', 'slave', '11111', 3,
                                  '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')
        server3 = base.TestServer('host3', 'master', '11113', 3,
                                  '111.11.1113', '222.22.2224')

        node_group1 = TestNodeGroup(
            'slave', [server1], ["DATANODE", "NODEMANAGER", "HDFS_CLIENT",
                                 "MAPREDUCE2_CLIENT"], 1)
        node_group2 = TestNodeGroup(
            'master1', [server2], ["NAMENODE", "ZOOKEEPER_SERVER",
                                   "JOURNALNODE"], 1)
        node_group3 = TestNodeGroup(
            'master2', [server3], ["RESOURCEMANAGER", "HISTORYSERVER",
                                   "ZOOKEEPER_SERVER", "AMBARI_SERVER",
                                   "JOURNALNODE"], 1)

        # Setup a cluster_configs resource with HDFS HA ON
        cc = {'HDFSHA': {'hdfs.nnha': True}}
        cc_r = rsc.Resource(cc)
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')

        # Test namenodes
        cluster1 = base.TestCluster([node_group1, node_group2, node_group3],
                                    cc_r)
        # should fail due to missing second namenode
        self.assertRaises(ex.NameNodeHAConfigurationError,
                          cluster_config.create_operational_config,
                          cluster1, [])

        # Test Journalnodes
        node_group2 = TestNodeGroup(
            'master1', [server2], ["NAMENODE", "ZOOKEEPER_SERVER"], 2)
        cluster1 = base.TestCluster([node_group1, node_group2, node_group3],
                                    cc_r)
        # should fail due to missing odd number greater than 3 of journalnodes
        self.assertRaises(ex.NameNodeHAConfigurationError,
                          cluster_config.create_operational_config,
                          cluster1, [])

        # Test zookeepers
        node_group2 = TestNodeGroup(
            'master1', [server2], ["NAMENODE", "JOURNALNODE"], 2)
        cluster1 = base.TestCluster([node_group1, node_group2, node_group3],
                                    cc_r)
        # should fail due to missing odd number greater than 3 of zookeepers
        self.assertRaises(ex.NameNodeHAConfigurationError,
                          cluster_config.create_operational_config,
                          cluster1, [])

        # should validate successfully now
        node_group2 = TestNodeGroup(
            'master1', [server2], ["NAMENODE", "JOURNALNODE",
                                   "ZOOKEEPER_SERVER"], 2)
        cluster1 = base.TestCluster([node_group1, node_group2, node_group3],
                                    cc_r)
        cluster_config.create_operational_config(cluster1, [])

        # Test when HDFS HA disabled
        cc = {'HDFSHA': {'hdfs.nnha': False}}
        cc_r = rsc.Resource(cc)

        node_group2 = TestNodeGroup(
            'master1', [server2], ["NAMENODE", "JOURNALNODE",
                                   "ZOOKEEPER_SERVER"], 1)
        cluster1 = base.TestCluster([node_group1, node_group2, node_group3],
                                    cc_r)

        # should fail due to using journalnode in non HDFS HA case
        self.assertRaises(ex.NameNodeHAConfigurationError,
                          cluster_config.create_operational_config,
                          cluster1, [])

        node_group2 = TestNodeGroup(
            'master1', [server2], ["NAMENODE", "ZKFC", "ZOOKEEPER_SERVER"], 1)

        cluster1 = base.TestCluster([node_group1, node_group2, node_group3],
                                    cc_r)

        # should fail due to using zkfc in non HDFS HA case
        self.assertRaises(ex.NameNodeHAConfigurationError,
                          cluster_config.create_operational_config,
                          cluster1, [])

    def test_validate_yarn(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "HDFS_CLIENT", "MAPREDUCE2_CLIENT"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER", "HISTORYSERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing JT
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "AMBARI_SERVER", "ZOOKEEPER_SERVER",
                                  "HISTORYSERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should cause validation exception due to 2 JT
        node_group3 = TestNodeGroup(
            'master', [server2], ["RESOURCEMANAGER"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

        # should cause validation exception due to 2 NN
        node_group3 = TestNodeGroup(
            'master', [server2], ["NAMENODE"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

        # should fail due to no nodemanager
        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "HDFS_CLIENT",
                                "MAPREDUCE2_CLIENT"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing JT
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

    def test_validate_hive(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "HIVE_CLIENT"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing hive_server
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HIVE_SERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER", "HISTORYSERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should cause validation exception due to 2 HIVE_SERVER
        node_group3 = TestNodeGroup(
            'master', [server2], ["HIVE_SERVER"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

    def test_validate_zk(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')
        server3 = base.TestServer('host3', 'master', '11113', 3,
                                  '111.11.1113', '222.22.2224')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "ZOOKEEPER_CLIENT"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "AMBARI_SERVER", "HISTORYSERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing ZOOKEEPER_SERVER
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "ZOOKEEPER_SERVER",
                                  "AMBARI_SERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should allow multiple ZOOKEEPER_SERVER processes
        node_group3 = TestNodeGroup(
            'zkserver', [server3], ["ZOOKEEPER_SERVER"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        cluster_config.create_operational_config(cluster, [])

    def test_validate_oozie(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "OOZIE_CLIENT"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing OOZIE_SERVER
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "OOZIE_SERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER", "HISTORYSERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should cause validation exception due to 2 OOZIE_SERVER
        node_group3 = TestNodeGroup(
            'master', [server2], ["OOZIE_SERVER"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

    def test_validate_ganglia(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "GANGLIA_MONITOR"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing GANGLIA_SERVER
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "GANGLIA_SERVER", "AMBARI_SERVER",
                                  "HISTORYSERVER", "ZOOKEEPER_SERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should cause validation exception due to 2 GANGLIA_SERVER
        node_group3 = TestNodeGroup(
            'master2', [server2], ["GANGLIA_SERVER"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

    def test_validate_ambari(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "AMBARI_AGENT"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing AMBARI_SERVER
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should cause validation exception due to 2 AMBARI_SERVER
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "AMBARI_SERVER", "ZOOKEEPER_SERVER"])
        node_group3 = TestNodeGroup(
            'master', [server2], ["AMBARI_SERVER"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        try:
            cluster_config.create_operational_config(cluster, [])
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

    def test_validate_hue(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "HUE"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing hive_server, oozie_server and
        # webhchat_server which is required by hue
        self.assertRaises(ex.RequiredServiceMissingException,
                          cluster_config.create_operational_config,
                          cluster, [])

        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HIVE_SERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER", "HISTORYSERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing oozie_server and webhchat_server, which
        # is required by hue
        self.assertRaises(ex.RequiredServiceMissingException,
                          cluster_config.create_operational_config,
                          cluster, [])

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "OOZIE_CLIENT", "HUE"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HIVE_SERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER", "HISTORYSERVER",
                                  "OOZIE_SERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should fail due to missing webhchat_server, which is required by hue
        self.assertRaises(ex.RequiredServiceMissingException,
                          cluster_config.create_operational_config,
                          cluster, [])

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "OOZIE_CLIENT", "HUE"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HIVE_SERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER", "HISTORYSERVER",
                                  "OOZIE_SERVER", "WEBHCAT_SERVER"])
        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # should validate successfully now
        cluster_config.create_operational_config(cluster, [])

        # should have automatically added a HIVE_CLIENT to "slave" node group
        hue_ngs = cluster_config.get_node_groups_containing_component("HUE")
        self.assertEqual(1, len(hue_ngs))
        self.assertIn("HIVE_CLIENT", hue_ngs.pop().components)

        # should cause validation exception due to 2 hue instances
        node_group3 = TestNodeGroup(
            'master', [server2], ["HUE"])
        cluster = base.TestCluster([node_group, node_group2, node_group3])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        self.assertRaises(ex.InvalidComponentCountException,
                          cluster_config.create_operational_config,
                          cluster, [])

    def test_validate_scaling_existing_ng(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # sanity check that original config validates
        cluster_config.create_operational_config(cluster, [])

        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        scaled_groups = {'master': 2}
        # should fail due to 2 JT
        try:
            cluster_config.create_operational_config(
                cluster, [], scaled_groups)
            self.fail('Validation should have thrown an exception')
        except ex.InvalidComponentCountException:
            # expected
            pass

    def test_scale(self, patched):

        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER",
                                "AMBARI_AGENT"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "ZOOKEEPER_SERVER",
                                  "AMBARI_SERVER"])

        cluster = base.TestCluster([node_group, node_group2])

        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # sanity check that original config validates
        cluster_config.create_operational_config(cluster, [])

        slave_ng = cluster_config.node_groups['slave']
        self.assertEqual(1, slave_ng.count)

        cluster_config.scale({'slave': 2})

        self.assertEqual(2, slave_ng.count)

    def test_get_deployed_configurations(self, patched):

        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        node_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER"])
        node_group2 = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "AMBARI_SERVER", "ZOOKEEPER_SERVER",
                                  "HISTORYSERVER"])

        cluster = base.TestCluster([node_group, node_group2])

        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        # sanity check that original config validates
        cluster_config.create_operational_config(cluster, [])
        configs = cluster_config.get_deployed_configurations()
        expected_configs = set(['mapred-site', 'ambari', 'hdfs-site',
                                'global', 'core-site', 'yarn-site'])
        self.assertEqual(expected_configs, expected_configs & configs)

    def test_get_deployed_node_group_count(self, patched):

        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        slave_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER"])
        slave2_group = TestNodeGroup(
            'slave2', [server], ["DATANODE", "NODEMANAGER"])
        master_group = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([master_group, slave_group, slave2_group])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        cluster_config.create_operational_config(cluster, [])

        self.assertEqual(2, cluster_config.get_deployed_node_group_count(
            'DATANODE'))
        self.assertEqual(1, cluster_config.get_deployed_node_group_count(
            'AMBARI_SERVER'))

    def test_get_node_groups_containing_component(self, patched):
        server = base.TestServer('host1', 'slave', '11111', 3,
                                 '111.11.1111', '222.22.2222')
        server2 = base.TestServer('host2', 'master', '11112', 3,
                                  '111.11.1112', '222.22.2223')

        slave_group = TestNodeGroup(
            'slave', [server], ["DATANODE", "NODEMANAGER"])
        slave2_group = TestNodeGroup(
            'slave2', [server], ["DATANODE", "NODEMANAGER"])
        master_group = TestNodeGroup(
            'master', [server2], ["NAMENODE", "RESOURCEMANAGER",
                                  "HISTORYSERVER", "AMBARI_SERVER",
                                  "ZOOKEEPER_SERVER"])

        cluster = base.TestCluster([master_group, slave_group, slave2_group])
        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        cluster_config.create_operational_config(cluster, [])

        datanode_ngs = cluster_config.get_node_groups_containing_component(
            'DATANODE')
        self.assertEqual(2, len(datanode_ngs))
        ng_names = set([datanode_ngs[0].name, datanode_ngs[1].name])
        self.assertIn('slave', ng_names)
        self.assertIn('slave2', ng_names)

    def test_get_components_for_type(self, patched):

        cluster_config = base.create_clusterspec(hdp_version='2.0.6')
        clients = cluster_config.get_components_for_type('CLIENT')
        slaves = cluster_config.get_components_for_type('SLAVE')
        masters = cluster_config.get_components_for_type('MASTER')

        expected_clients = set(['HCAT', 'ZOOKEEPER_CLIENT',
                                'MAPREDUCE2_CLIENT', 'HIVE_CLIENT',
                                'HDFS_CLIENT', 'PIG', 'YARN_CLIENT', 'HUE'])
        self.assertEqual(expected_clients, expected_clients & set(clients))

        expected_slaves = set(['AMBARI_AGENT', 'NODEMANAGER', 'DATANODE',
                               'GANGLIA_MONITOR'])
        self.assertEqual(expected_slaves, expected_slaves & set(slaves))

        expected_masters = set(['SECONDARY_NAMENODE', 'HIVE_METASTORE',
                                'AMBARI_SERVER', 'RESOURCEMANAGER',
                                'WEBHCAT_SERVER', 'NAGIOS_SERVER',
                                'MYSQL_SERVER', 'ZOOKEEPER_SERVER',
                                'NAMENODE', 'HIVE_SERVER', 'GANGLIA_SERVER'])
        self.assertEqual(expected_masters, expected_masters & set(masters))

    def _assert_services(self, services):
        found_services = []
        for service in services:
            name = service.name
            found_services.append(name)
            self.service_validators[name](service)

        self.assertEqual(15, len(found_services))
        self.assertIn('HDFS', found_services)
        self.assertIn('MAPREDUCE2', found_services)
        self.assertIn('GANGLIA', found_services)
        self.assertIn('NAGIOS', found_services)
        self.assertIn('AMBARI', found_services)
        self.assertIn('PIG', found_services)
        self.assertIn('HIVE', found_services)
        self.assertIn('HCATALOG', found_services)
        self.assertIn('ZOOKEEPER', found_services)
        self.assertIn('WEBHCAT', found_services)
        self.assertIn('OOZIE', found_services)
        self.assertIn('SQOOP', found_services)
        self.assertIn('HBASE', found_services)
        self.assertIn('HUE', found_services)

    def _assert_hdfs(self, service):
        self.assertEqual('HDFS', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(6, len(found_components))
        self._assert_component('NAMENODE', 'MASTER', "1",
                               found_components['NAMENODE'])
        self._assert_component('DATANODE', 'SLAVE', "1+",
                               found_components['DATANODE'])
        self._assert_component('SECONDARY_NAMENODE', 'MASTER', "1",
                               found_components['SECONDARY_NAMENODE'])
        self._assert_component('HDFS_CLIENT', 'CLIENT', "1+",
                               found_components['HDFS_CLIENT'])
        self._assert_component('JOURNALNODE', 'MASTER', "1+",
                               found_components['JOURNALNODE'])
        self._assert_component('ZKFC', 'MASTER', "1+",
                               found_components['ZKFC'])
        # TODO(jspeidel) config

    def _assert_mrv2(self, service):
        self.assertEqual('MAPREDUCE2', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(2, len(found_components))
        self._assert_component('HISTORYSERVER', 'MASTER', "1",
                               found_components['HISTORYSERVER'])
        self._assert_component('MAPREDUCE2_CLIENT', 'CLIENT', "1+",
                               found_components['MAPREDUCE2_CLIENT'])

    def _assert_yarn(self, service):
        self.assertEqual('YARN', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(3, len(found_components))
        self._assert_component('RESOURCEMANAGER', 'MASTER', "1",
                               found_components['RESOURCEMANAGER'])
        self._assert_component('NODEMANAGER', 'SLAVE', "1+",
                               found_components['NODEMANAGER'])
        self._assert_component('YARN_CLIENT', 'CLIENT', "1+",
                               found_components['YARN_CLIENT'])

    def _assert_nagios(self, service):
        self.assertEqual('NAGIOS', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(1, len(found_components))
        self._assert_component('NAGIOS_SERVER', 'MASTER', "1",
                               found_components['NAGIOS_SERVER'])

    def _assert_ganglia(self, service):
        self.assertEqual('GANGLIA', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(2, len(found_components))
        self._assert_component('GANGLIA_SERVER', 'MASTER', "1",
                               found_components['GANGLIA_SERVER'])
        self._assert_component('GANGLIA_MONITOR', 'SLAVE', "1+",
                               found_components['GANGLIA_MONITOR'])

    def _assert_ambari(self, service):
        self.assertEqual('AMBARI', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(2, len(found_components))
        self._assert_component('AMBARI_SERVER', 'MASTER', "1",
                               found_components['AMBARI_SERVER'])
        self._assert_component('AMBARI_AGENT', 'SLAVE', "1+",
                               found_components['AMBARI_AGENT'])

        self.assertEqual(1, len(service.users))
        user = service.users[0]
        self.assertEqual('admin', user.name)
        self.assertEqual('admin', user.password)
        groups = user.groups
        self.assertEqual(1, len(groups))
        self.assertIn('admin', groups)

    def _assert_pig(self, service):
        self.assertEqual('PIG', service.name)
        self.assertEqual(1, len(service.components))
        self.assertEqual('PIG', service.components[0].name)

    def _assert_hive(self, service):
        self.assertEqual('HIVE', service.name)
        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(4, len(found_components))
        self._assert_component('HIVE_SERVER', 'MASTER', "1",
                               found_components['HIVE_SERVER'])
        self._assert_component('HIVE_METASTORE', 'MASTER', "1",
                               found_components['HIVE_METASTORE'])
        self._assert_component('MYSQL_SERVER', 'MASTER', "1",
                               found_components['MYSQL_SERVER'])
        self._assert_component('HIVE_CLIENT', 'CLIENT', "1+",
                               found_components['HIVE_CLIENT'])

    def _assert_hcatalog(self, service):
        self.assertEqual('HCATALOG', service.name)
        self.assertEqual(1, len(service.components))
        self.assertEqual('HCAT', service.components[0].name)

    def _assert_zookeeper(self, service):
        self.assertEqual('ZOOKEEPER', service.name)
        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(2, len(found_components))
        self._assert_component('ZOOKEEPER_SERVER', 'MASTER', "1+",
                               found_components['ZOOKEEPER_SERVER'])
        self._assert_component('ZOOKEEPER_CLIENT', 'CLIENT', "1+",
                               found_components['ZOOKEEPER_CLIENT'])

    def _assert_webhcat(self, service):
        self.assertEqual('WEBHCAT', service.name)
        self.assertEqual(1, len(service.components))
        self.assertEqual('WEBHCAT_SERVER', service.components[0].name)

    def _assert_oozie(self, service):
        self.assertEqual('OOZIE', service.name)
        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(2, len(found_components))
        self._assert_component('OOZIE_SERVER', 'MASTER', "1",
                               found_components['OOZIE_SERVER'])
        self._assert_component('OOZIE_CLIENT', 'CLIENT', "1+",
                               found_components['OOZIE_CLIENT'])

    def _assert_sqoop(self, service):
        self.assertEqual('SQOOP', service.name)
        self.assertEqual(1, len(service.components))
        self.assertEqual('SQOOP', service.components[0].name)

    def _assert_hbase(self, service):
        self.assertEqual('HBASE', service.name)
        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(3, len(found_components))
        self._assert_component('HBASE_MASTER', 'MASTER', "1",
                               found_components['HBASE_MASTER'])
        self._assert_component('HBASE_REGIONSERVER', 'SLAVE', "1+",
                               found_components['HBASE_REGIONSERVER'])
        self._assert_component('HBASE_CLIENT', 'CLIENT', "1+",
                               found_components['HBASE_CLIENT'])

    def _assert_hue(self, service):
        self.assertEqual('HUE', service.name)
        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(1, len(found_components))
        self._assert_component('HUE', 'CLIENT', "1",
                               found_components['HUE'])

    def _assert_component(self, name, comp_type, cardinality, component):
        self.assertEqual(name, component.name)
        self.assertEqual(comp_type, component.type)
        self.assertEqual(cardinality, component.cardinality)

    def _assert_configurations(self, configurations):
        self.assertEqual(17, len(configurations))
        self.assertIn('global', configurations)
        self.assertIn('core-site', configurations)
        self.assertIn('yarn-site', configurations)
        self.assertIn('mapred-site', configurations)
        self.assertIn('hdfs-site', configurations)
        self.assertIn('ambari', configurations)
        self.assertIn('webhcat-site', configurations)
        self.assertIn('hive-site', configurations)
        self.assertIn('oozie-site', configurations)
        self.assertIn('hbase-site', configurations)
        self.assertIn('capacity-scheduler', configurations)
        self.assertIn('hue-ini', configurations)
        self.assertIn('hue-core-site', configurations)
        self.assertIn('hue-hdfs-site', configurations)
        self.assertIn('hue-webhcat-site', configurations)
        self.assertIn('hue-oozie-site', configurations)
        self.assertIn('hdfsha', configurations)


class TestNodeGroup(object):
    def __init__(self, name, instances, node_processes, count=1):
        self.name = name
        self.instances = instances
        for i in instances:
            i.node_group = self
        self.node_processes = node_processes
        self.count = count
        self.id = name

    def storage_paths(self):
        return ['']


class TestUserInputConfig(object):
    def __init__(self, tag, target, name):
        self.tag = tag
        self.applicable_target = target
        self.name = name
