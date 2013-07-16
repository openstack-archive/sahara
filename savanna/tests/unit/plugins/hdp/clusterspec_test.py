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

import os
from savanna.plugins.hdp import clusterspec as cs
import unittest2


class ClusterSpecTest(unittest2.TestCase):
    service_validators = {}

    #TODO(jspeidel): test host manifest

    def test_parse_default_with_hosts(self):
        with open(os.path.join(os.path.realpath('../plugins'), 'hdp',
                               'resources',
                               'default-cluster.template'), 'r') as f:
            cluster_config_file = f.read()

        servers = []
        server1 = TestServer('host1', 'master', '11111', 3, '111.11.1111',
                             '222.11.1111',
                             node_processes=["namenode", "jobtracker",
                                             "secondary_namenode",
                                             "ganglia_server",
                                             "ganglia_monitor",
                                             "nagios_server", "AMBARI_SERVER",
                                             "ambari_agent"])
        server2 = TestServer('host2', 'slave', '11111', 3, '222.22.2222',
                             '333.22.2222')
        servers.append(server1)
        servers.append(server2)

        cluster = TestCluster()
        cluster.instances = servers

        cluster_config = cs.ClusterSpec(cluster_config_file, cluster)

        self._assert_services(cluster_config.services)
        self._assert_configurations(cluster_config.configurations)
        self._assert_host_role_mappings(cluster_config.node_groups)

        return cluster_config

    def test_select_correct_server_for_ambari_host(self):
        with open(os.path.join(os.path.realpath('../plugins'), 'hdp',
                               'resources',
                               'default-cluster.template'), 'r') as f:
            cluster_config_file = f.read()

        servers = []
        server1 = TestServer('ambari_machine', 'master', '11111', 3,
                             '111.11.1111', '222.11.1111',
                             node_processes=["namenode", "jobtracker",
                                             "secondary_namenode",
                                             "ganglia_server",
                                             "ganglia_monitor",
                                             "nagios_server", "AMBARI_SERVER",
                                             "ambari_agent"])
        server2 = TestServer('host2', 'slave', '11111', 3, '222.22.2222',
                             '333.22.2222',
                             node_processes=["datanode", "tasktracker",
                                             "ganglia_monitor", "hdfs_client",
                                             "mapreduce_client",
                                             "ambari_agent"])
        servers.append(server1)
        servers.append(server2)

        cluster = TestCluster
        cluster.instances = servers

        cluster_config = cs.ClusterSpec(cluster_config_file, cluster)
        self.assertIn('ambari_machine', cluster_config.str,
                      'Ambari host not found')

    def test_parse_default(self):
        with open(os.path.join(os.path.realpath('../plugins'), 'hdp',
                               'resources',
                               'default-cluster.template'), 'r') as f:
            cluster_config_file = f.read()

        cluster_config = cs.ClusterSpec(cluster_config_file)

        self._assert_services(cluster_config.services)
        self._assert_configurations(cluster_config.configurations)
        self._assert_host_role_mappings(cluster_config.node_groups)

        return cluster_config

    def test_normalize(self):
        with open(os.path.join(os.path.realpath('../plugins'), 'hdp',
                               'resources',
                               'default-cluster.template'), 'r') as f:
            cluster_config_file = f.read()

        cluster_config = cs.ClusterSpec(cluster_config_file)
        cluster = cluster_config.normalize()

        configs = cluster.cluster_configs
        contains_dfs_datanode_http_address = False
        contains_mapred_jobtracker_taskScheduler = False
        contains_dfs_include = False

        for entry in configs:
            config = entry.config
            # assert some random configurations across targets
            if config.name == 'dfs.datanode.http.address':
                contains_dfs_datanode_http_address = True
                self.assertEquals('string', config.type)
                self.assertEquals('0.0.0.0:50075', config.default_value)
                self.assertEquals('service:HDFS', config.applicable_target)

            if config.name == 'mapred.jobtracker.taskScheduler':
                contains_mapred_jobtracker_taskScheduler = True
                self.assertEquals('string', config.type)
                self.assertEquals(
                    'org.apache.hadoop.mapred.CapacityTaskScheduler',
                    config.default_value)
                self.assertEquals('service:MAPREDUCE',
                                  config.applicable_target)

            if config.name == 'dfs_include':
                contains_dfs_include = True
                self.assertEquals('string', config.type)
                self.assertEquals('dfs.include', config.default_value)
                self.assertEquals('service:HDFS', config.applicable_target)

                #            print 'Config: name: {0}, type:{1},
                # default value:{2}, target:{3}, Value:{4}'.format(
                #                config.name, config.type,
                # config.default_value,
                #  config.applicable_target, entry.value)

        self.assertTrue(contains_dfs_datanode_http_address)
        self.assertTrue(contains_mapred_jobtracker_taskScheduler)
        self.assertTrue(contains_dfs_include)
        node_groups = cluster.node_groups
        self.assertEquals(2, len(node_groups))
        contains_master_group = False
        contains_slave_group = False
        for i in range(2):
            node_group = node_groups[i]
            components = node_group.node_processes
            if node_group.name == "MASTER":
                contains_master_group = True
                self.assertEquals(8, len(components))
                self.assertIn('NAMENODE', components)
                self.assertIn('JOBTRACKER', components)
                self.assertIn('SECONDARY_NAMENODE', components)
                self.assertIn('GANGLIA_SERVER', components)
                self.assertIn('GANGLIA_MONITOR', components)
                self.assertIn('NAGIOS_SERVER', components)
                self.assertIn('AMBARI_SERVER', components)
                self.assertIn('AMBARI_AGENT', components)
                #TODO(jspeidel): node configs
                #TODO(jspeidel): vm_requirements
            elif node_group.name == 'SLAVE':
                contains_slave_group = True
                self.assertEquals(6, len(components))
                self.assertIn('DATANODE', components)
                self.assertIn('TASKTRACKER', components)
                self.assertIn('GANGLIA_MONITOR', components)
                self.assertIn('HDFS_CLIENT', components)
                self.assertIn('MAPREDUCE_CLIENT', components)
                self.assertIn('AMBARI_AGENT', components)
                #TODO(jspeidel): node configs
                #TODO(jspeidel): vm requirements
            else:
                self.fail('Unexpected node group: {0}'.format(node_group.name))
        self.assertTrue(contains_master_group)
        self.assertTrue(contains_slave_group)

    def _assert_services(self, services):
        found_services = []
        for service in services:
            name = service.name
            found_services.append(name)
            self.service_validators[name](service)

        self.assertEquals(5, len(found_services))
        self.assertIn('HDFS', found_services)
        self.assertIn('MAPREDUCE', found_services)
        self.assertIn('GANGLIA', found_services)
        self.assertIn('NAGIOS', found_services)
        self.assertIn('AMBARI', found_services)

    def _assert_hdfs(self, service):
        self.assertEquals('HDFS', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(4, len(found_components))
        self._assert_component('NAMENODE', 'MASTER', "1",
                               found_components['NAMENODE'])
        self._assert_component('DATANODE', 'SLAVE', "1+",
                               found_components['DATANODE'])
        self._assert_component('SECONDARY_NAMENODE', 'MASTER', "1",
                               found_components['SECONDARY_NAMENODE'])
        self._assert_component('HDFS_CLIENT', 'CLIENT', "1+",
                               found_components['HDFS_CLIENT'])
        #TODO(jspeidel) config

    def _assert_mr(self, service):
        self.assertEquals('MAPREDUCE', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(3, len(found_components))
        self._assert_component('JOBTRACKER', 'MASTER', "1",
                               found_components['JOBTRACKER'])
        self._assert_component('TASKTRACKER', 'SLAVE', "1+",
                               found_components['TASKTRACKER'])
        self._assert_component('MAPREDUCE_CLIENT', 'CLIENT', "1+",
                               found_components['MAPREDUCE_CLIENT'])
        # TODO(jspeidel) config

    def _assert_nagios(self, service):
        self.assertEquals('NAGIOS', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(1, len(found_components))
        self._assert_component('NAGIOS_SERVER', 'MASTER', "1",
                               found_components['NAGIOS_SERVER'])

    def _assert_ganglia(self, service):
        self.assertEquals('GANGLIA', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(2, len(found_components))
        self._assert_component('GANGLIA_SERVER', 'MASTER', "1",
                               found_components['GANGLIA_SERVER'])
        self._assert_component('GANGLIA_MONITOR', 'SLAVE', "1+",
                               found_components['GANGLIA_MONITOR'])

    def _assert_ambari(self, service):
        self.assertEquals('AMBARI', service.name)

        found_components = {}
        for component in service.components:
            found_components[component.name] = component

        self.assertEqual(2, len(found_components))
        self._assert_component('AMBARI_SERVER', 'MASTER', "1",
                               found_components['AMBARI_SERVER'])
        self._assert_component('AMBARI_AGENT', 'SLAVE', "1+",
                               found_components['AMBARI_AGENT'])

    def _assert_component(self, name, comp_type, cardinality, component):
        self.assertEquals(name, component.name)
        self.assertEquals(comp_type, component.type)
        self.assertEquals(cardinality, component.cardinality)

    def _assert_configurations(self, configurations):
        self.assertEquals(4, len(configurations))
        self.assertIn('global', configurations)
        self.assertIn('core-site', configurations)
        self.assertIn('mapred-site', configurations)
        self.assertIn('hdfs-site', configurations)

    def _assert_host_role_mappings(self, node_groups):
        self.assertEquals(2, len(node_groups))
        self.assertIn('MASTER', node_groups)
        self.assertIn('SLAVE', node_groups)

        master_node_group = node_groups['MASTER']
        self.assertEquals('MASTER', master_node_group.name)
        self.assertEquals(None, master_node_group.predicate)
        self.assertEquals('1', master_node_group.cardinality)
        self.assertEquals(1, master_node_group.default_count)
        self.assertEquals(8, len(master_node_group.components))
        self.assertIn('NAMENODE', master_node_group.components)
        self.assertIn('JOBTRACKER', master_node_group.components)
        self.assertIn('SECONDARY_NAMENODE', master_node_group.components)
        self.assertIn('GANGLIA_SERVER', master_node_group.components)
        self.assertIn('GANGLIA_MONITOR', master_node_group.components)
        self.assertIn('NAGIOS_SERVER', master_node_group.components)
        self.assertIn('AMBARI_SERVER', master_node_group.components)
        self.assertIn('AMBARI_AGENT', master_node_group.components)

        slave_node_group = node_groups['SLAVE']
        self.assertEquals('SLAVE', slave_node_group.name)
        self.assertEquals(None, slave_node_group.predicate)
        self.assertEquals('1+', slave_node_group.cardinality)
        self.assertEquals(2, slave_node_group.default_count)
        self.assertEquals(6, len(slave_node_group.components))
        self.assertIn('DATANODE', slave_node_group.components)
        self.assertIn('TASKTRACKER', slave_node_group.components)
        self.assertIn('GANGLIA_MONITOR', slave_node_group.components)
        self.assertIn('HDFS_CLIENT', slave_node_group.components)
        self.assertIn('MAPREDUCE_CLIENT', slave_node_group.components)
        self.assertIn('AMBARI_AGENT', slave_node_group.components)

    def setUp(self):
        self.service_validators['HDFS'] = self._assert_hdfs
        self.service_validators['MAPREDUCE'] = self._assert_mr
        self.service_validators['GANGLIA'] = self._assert_ganglia
        self.service_validators['NAGIOS'] = self._assert_nagios
        self.service_validators['AMBARI'] = self._assert_ambari


class TestServer():
    def __init__(self, hostname, role, img, flavor, public_ip, private_ip,
                 node_processes=None):
        self.hostname = hostname
        self.fqdn = hostname
        self.role = role
        self.nova_info = TestNova
        self.nova_info.image = img
        self.nova_info.flavor = flavor
        self.management_ip = public_ip
        self.public_ip = public_ip
        self.internal_ip = private_ip
        self.node_processes = node_processes


class TestNova():
    image = None
    flavor = None


class TestCluster():
    instances = []
