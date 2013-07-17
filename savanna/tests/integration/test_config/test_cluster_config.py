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
import savanna.tests.integration.configs.parameters as param


def _add_config(body, config):
    if config in [param.NAMENODE_CONFIG, param.DATANODE_CONFIG]:
        body['node_configs']['HDFS'] = config
    elif config == param.GENERAL_CONFIG:
        body['cluster_configs']['general'] = config
    elif config == param.CLUSTER_HDFS_CONFIG:
        body['cluster_configs']['HDFS'] = config
    elif config == param.CLUSTER_MAPREDUCE_CONFIG:
        body['cluster_configs']['MapReduce'] = config
    else:
        body['node_configs']['MapReduce'] = config


class ClusterConfigTest(base.ITestCase):

    def setUp(self):
        super(ClusterConfigTest, self).setUp()
        telnetlib.Telnet(self.host, self.port)

    def assertConfigs(self, get_config, param_config):
        self.assertEqual(get_config, param_config,
                         msg='configs are not equal: %s != %s'
                             % (str(get_config), str(param_config)))

    def assertConfigOnNode(self, host, config, value):
        conf = config.replace(' ', '')
        com = self.execute_command(host, './script.sh %s -val %s -url %s' %
                                         (conf, value, param.OS_AUTH_URL))
        self.assertEqual(com[0], 0,
                         msg='host: %s, config %s is not equal: %s'
                             % (host, config, value))

    def _cluster_config_testing(self, cluster_body):
        cluster_id = None
        try:
            _add_config(cluster_body, param.GENERAL_CONFIG)
            _add_config(cluster_body, param.CLUSTER_HDFS_CONFIG)
            _add_config(cluster_body, param.CLUSTER_MAPREDUCE_CONFIG)
            cluster_id = self.create_cluster_and_get_id(cluster_body)
            get_data = self.get_object(self.url_cluster_with_slash,
                                       cluster_id, 200, True)
            get_data = get_data['cluster']
            self.assertConfigs(get_data['cluster_configs']['general'],
                               param.GENERAL_CONFIG)
            self.assertConfigs(get_data['cluster_configs']['HDFS'],
                               param.CLUSTER_HDFS_CONFIG)
            self.assertConfigs(get_data['cluster_configs']['MapReduce'],
                               param.CLUSTER_MAPREDUCE_CONFIG)
            node_groups = get_data['node_groups']
            ip_instances = {}
            process_map = {
                'namenode': {
                    'service': 'HDFS', 'param': param.NAMENODE_CONFIG},
                'jobtracker': {
                    'service': 'MapReduce', 'param': param.JOBTRACKER_CONFIG},
                'datanode': {
                    'service': 'HDFS', 'param': param.DATANODE_CONFIG},
                'tasktracker': {
                    'service': 'MapReduce', 'param': param.TASKTRACKER_CONFIG}
            }

            def get_node_configs(node_group, process):
                return \
                    node_group['node_configs'][process_map[process]['service']]

            def get_param(process):
                return process_map[process]['param']

            for node_group in node_groups:
                for process in node_group['node_processes']:
                    self.assertConfigs(
                        get_node_configs(node_group,
                                         process), get_param(process))
                instances = node_group['instances']
                for instans in instances:
                    management_ip = instans['management_ip']
                    self.transfer_script_to_node(
                        management_ip, 'test_config/config_test_script.sh')
                    ip_instances[management_ip] = node_group[
                        'node_processes']
            try:
                for key, processes in ip_instances.items():
                    telnetlib.Telnet(key, '22')
                    for conf, value in param.CLUSTER_MAPREDUCE_CONFIG.items():
                        self.assertConfigOnNode(key, conf, value)
                    for conf, value in param.CLUSTER_HDFS_CONFIG.items():
                        self.assertConfigOnNode(key, conf, value)
                    for process in processes:
                        for sec_key, sec_value in get_param(process).items():
                            self.assertConfigOnNode(key, sec_key, sec_value)
                    if 'namenode' in processes:
                        for sec_key, sec_value in param.GENERAL_CONFIG.items():
                            self.assertConfigOnNode(
                                key, sec_key, sec_value)
            except Exception as e:
                self.fail(e.message)
        except Exception as e:
            self.fail(e.message)
        finally:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)

    def test_cluster_config_nnjt_ttdn(self):
        id_master_ngt = None
        id_worker_ngt = None
        try:
            master_ngt_body = self.make_node_group_template(
                'master-ngt', 'qa probe', 'JT+NN')
            _add_config(master_ngt_body, param.NAMENODE_CONFIG)
            _add_config(master_ngt_body, param.JOBTRACKER_CONFIG)
            id_master_ngt = self.get_object_id(
                'node_group_template', self.post_object(self.url_ngt,
                                                        master_ngt_body, 202))

            worker_ngt_body = self.make_node_group_template(
                'worker-ngt', 'qa probe', 'TT+DN')
            _add_config(worker_ngt_body, param.DATANODE_CONFIG)
            _add_config(worker_ngt_body, param.TASKTRACKER_CONFIG)
            id_worker_ngt = self.get_object_id(
                'node_group_template', self.post_object(self.url_ngt,
                                                        worker_ngt_body, 202))

            ngt_id_list = {id_master_ngt: 1, id_worker_ngt: 2}
            cl_body = self.make_cl_body_node_group_templates(ngt_id_list)
            self._cluster_config_testing(cl_body)
        except Exception as e:
            self.fail(str(e))
        finally:
            self.del_object(self.url_ngt_with_slash, id_master_ngt, 204)
            self.del_object(self.url_ngt_with_slash, id_worker_ngt, 204)
