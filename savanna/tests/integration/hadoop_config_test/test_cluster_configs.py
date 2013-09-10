# Copyright (c) 2013 Mirantis Inc.
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

import telnetlib

from savanna.tests.integration import base
import savanna.tests.integration.configs.parameters.common_parameters as param
import savanna.tests.integration.configs.parameters.vanilla_parameters as v_prm


NAMENODE_CONFIG = {'Name Node Heap Size': 510}
JOBTRACKER_CONFIG = {'Job Tracker Heap Size': 512}

DATANODE_CONFIG = {'Data Node Heap Size': 511}
TASKTRACKER_CONFIG = {'Task Tracker Heap Size': 513}

GENERAL_CONFIG = {'Enable Swift': True}

CLUSTER_HDFS_CONFIG = {'dfs.replication': 2}
CLUSTER_MAPREDUCE_CONFIG = {'mapred.map.tasks.speculative.execution': False,
                            'mapred.child.java.opts': '-Xmx500m'}


def _add_config(body, config_type, service, config):
    body[config_type][service] = config


@base.enable_test(param.ENABLE_CONFIG_TESTS)
class ClusterConfigTest(base.ITestCase):

    def setUp(self):
        super(ClusterConfigTest, self).setUp()

        telnetlib.Telnet(self.host, self.port)

    def assertConfigs(self, get_config, param_config):
        self.assertEqual(get_config, param_config,
                         'Configs are not equal: \'%s\' != \'%s\''
                         % (str(get_config), str(param_config)))

    def assertConfigOnNode(self, host, config, value):
        conf = config.replace(' ', '')
        com = self.execute_command(host, './script.sh %s -val %s -url %s'
                                         % (conf, value, param.OS_AUTH_URL),
                                   v_prm.NODE_USERNAME)
        self.assertEqual(com[0], 0,
                         'Host: %s, config \'%s\' is not equal \'%s\''
                         % (host, config, value))

    def _cluster_config_testing(self, cluster_id):
        get_data = self.get_object(self.url_cluster_with_slash,
                                   cluster_id, 200, True)
        get_data = get_data['cluster']

        self.assertConfigs(get_data['cluster_configs']['general'],
                           GENERAL_CONFIG)
        self.assertConfigs(get_data['cluster_configs']['HDFS'],
                           CLUSTER_HDFS_CONFIG)
        self.assertConfigs(get_data['cluster_configs']['MapReduce'],
                           CLUSTER_MAPREDUCE_CONFIG)

        process_map = {
            'namenode': {
                'service': 'HDFS', 'param': NAMENODE_CONFIG
            },
            'jobtracker': {
                'service': 'MapReduce',
                'param': JOBTRACKER_CONFIG
            },
            'datanode': {
                'service': 'HDFS', 'param': DATANODE_CONFIG
            },
            'tasktracker': {
                'service': 'MapReduce', 'param': TASKTRACKER_CONFIG
            }
        }

        def get_node_configs(node_group, process):
            return \
                node_group['node_configs'][process_map[process]['service']]

        def get_param(process):
            return process_map[process]['param']

        node_groups = get_data['node_groups']
        ip_instances = {}
        for node_group in node_groups:
            for process in node_group['node_processes']:
                self.assertConfigs(
                    get_node_configs(node_group, process),
                    get_param(process)
                )

            instances = node_group['instances']
            for instans in instances:
                management_ip = instans['management_ip']
                self.transfer_script_to_node(
                    management_ip, v_prm.NODE_USERNAME,
                    'hadoop_config_test/hadoop_config_test_script.sh'
                )
                ip_instances[management_ip] = node_group[
                    'node_processes']

        for key, processes in ip_instances.items():
            telnetlib.Telnet(key, '22')

            for conf, value in CLUSTER_MAPREDUCE_CONFIG.items():
                self.assertConfigOnNode(key, conf, value)

            for conf, value in CLUSTER_HDFS_CONFIG.items():
                self.assertConfigOnNode(key, conf, value)

            for process in processes:
                for sec_key, sec_value in get_param(process).items():
                    self.assertConfigOnNode(key, sec_key, sec_value)

            if 'namenode' in processes:
                for sec_key, sec_value in GENERAL_CONFIG.items():
                    self.assertConfigOnNode(key, sec_key, sec_value)

    def test_cluster_config_nnjt_ttdn(self):
        master_ngt_body = self.make_node_group_template(
            'master-ngt', 'qa probe', 'JT+NN')
        _add_config(master_ngt_body, 'node_configs', 'HDFS', NAMENODE_CONFIG)
        _add_config(master_ngt_body, 'node_configs', 'MapReduce',
                    JOBTRACKER_CONFIG)

        worker_ngt_body = self.make_node_group_template(
            'worker-ngt', 'qa probe', 'TT+DN')
        _add_config(worker_ngt_body, 'node_configs', 'HDFS', DATANODE_CONFIG)
        _add_config(worker_ngt_body, 'node_configs', 'MapReduce',
                    TASKTRACKER_CONFIG)

        try:
            id_master_ngt = self.get_object_id(
                'node_group_template', self.post_object(self.url_ngt,
                                                        master_ngt_body, 202)
            )
        except Exception as e:
            self.fail('Failure while master node group template creation: ' +
                      str(e))

        try:
            id_worker_ngt = self.get_object_id(
                'node_group_template', self.post_object(self.url_ngt,
                                                        worker_ngt_body, 202)
            )
        except Exception as e:
            self.del_object(self.url_ngt_with_slash, id_master_ngt, 204)
            self.fail('Failure while worker node group template creation: ' +
                      str(e))

        ngt_id_list = {id_master_ngt: 1, id_worker_ngt: 2}
        cluster_body = self.make_cl_body_node_group_templates(ngt_id_list)

        _add_config(cluster_body, 'cluster_configs', 'general', GENERAL_CONFIG)
        _add_config(cluster_body, 'cluster_configs', 'HDFS',
                    CLUSTER_HDFS_CONFIG)
        _add_config(cluster_body, 'cluster_configs', 'MapReduce',
                    CLUSTER_MAPREDUCE_CONFIG)

        try:
            cluster_id = self.create_cluster_and_get_id(cluster_body)

        except Exception as e:
            self.del_object(self.url_ngt_with_slash, id_master_ngt, 204)
            self.del_object(self.url_ngt_with_slash, id_worker_ngt, 204)
            self.fail('Failure while cluster creation: ' + str(e))

        try:
            self._cluster_config_testing(cluster_id)

        except Exception as e:
            self.fail('Failure while config comparison: ' + str(e))

        finally:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.del_object(self.url_ngt_with_slash, id_master_ngt, 204)
            self.del_object(self.url_ngt_with_slash, id_worker_ngt, 204)
