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
import savanna.tests.integration.configs.parameters.hdp_parameters as hdp_param
import savanna.tests.integration.configs.parameters.vanilla_parameters as v_prm


class HadoopTest(base.ITestCase):

    def setUp(self):
        super(HadoopTest, self).setUp()

        telnetlib.Telnet(self.host, self.port)

    def _hadoop_testing(self, cluster_body, plugin_name, hadoop_version,
                        hadoop_user, hadoop_directory, hadoop_log_directory,
                        node_username):
        cluster_id = self.create_cluster_and_get_id(cluster_body)

        try:
            ip_instances = self.get_instances_ip_and_node_processes_list(
                cluster_id)

            clstr_info = self.get_namenode_ip_and_tt_dn_count(ip_instances,
                                                              plugin_name)
            namenode_ip = clstr_info['namenode_ip']
            node_count = clstr_info['node_count']

            self.await_active_workers_for_namenode(clstr_info,
                                                   node_username, hadoop_user)

        except Exception as e:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.fail('Failure: ' + str(e))

        try:
            for node_ip in ip_instances:
                self.transfer_script_to_node(node_ip, node_username)

        except Exception as e:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.fail('Failure while script transferring: ' + str(e))

        try:
            self.execute_command(
                namenode_ip,
                './script.sh pi -nc %s -hv %s -hd %s -hu %s -pn %s'
                % (node_count,
                   hadoop_version,
                   hadoop_directory,
                   hadoop_user,
                   plugin_name), node_username)

        except Exception as e:
            print(self.read_file_from(namenode_ip,
                                      '/tmp/outputTestMapReduce/log.txt',
                                      node_username))
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.fail('Failure while PI-job launch: ' + str(e))

        try:
            job_name = self.execute_command(namenode_ip, './script.sh gn',
                                            node_username)

            if job_name[1] == 'JobId':
                self.fail('PI-job has not been launched')

            self.assertEqual(job_name[0], 0)

        except Exception as e:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.fail('Failure while job name obtaining: ' + str(e))

        try:
            for node_ip, process_list in ip_instances.items():
                if self.tt in process_list:
                    self.assertEqual(
                        self.execute_command(
                            node_ip, './script.sh ed -jn %s -hld %s'
                            % (job_name[1][:-1], hadoop_log_directory),
                            node_username
                        )[0], 0,
                        'Host %s: not found log file of PI-job work' % node_ip)

        except Exception as e:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.fail('Failure: ' + str(e))

        try:
            self.assertEqual(
                self.execute_command(
                    namenode_ip,
                    './script.sh mr -hv %s -hd %s -hu %s -pn %s'
                    % (hadoop_version,
                       hadoop_directory,
                       hadoop_user,
                       plugin_name), node_username
                )[0], 0)

        except Exception as e:
            print(self.read_file_from(namenode_ip,
                                      '/tmp/outputTestMapReduce/log.txt',
                                      node_username))
            self.fail('Failure while HDFS check: ' + str(e))

        finally:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)

    @base.enable_test(param.ENABLE_HADOOP_TESTS_FOR_VANILLA_PLUGIN)
    def test_hadoop_single_master_for_vanilla_plugin(self):
        """This test checks Hadoop work for "Vanilla" plugin
        """
        node_processes = {'JT+NN': 1, 'TT+DN': 2}

        cluster_body = self.make_vanilla_cl_body_node_processes(node_processes)

        self._hadoop_testing(cluster_body,
                             v_prm.PLUGIN_NAME,
                             v_prm.HADOOP_VERSION,
                             v_prm.HADOOP_USER,
                             v_prm.HADOOP_DIRECTORY,
                             v_prm.HADOOP_LOG_DIRECTORY,
                             v_prm.NODE_USERNAME)

    @base.enable_test(param.ENABLE_HADOOP_TESTS_FOR_HDP_PLUGIN)
    def test_hadoop_single_master_for_hdp_plugin(self):
        """This test checks Hadoop work for "HDP" plugin
        """
        node_processes = {'JT+NN': 1, 'TT+DN': 2}

        cluster_body = self.make_hdp_cl_body_node_processes(node_processes)

        self._hadoop_testing(cluster_body,
                             hdp_param.PLUGIN_NAME,
                             hdp_param.HADOOP_VERSION,
                             hdp_param.HADOOP_USER,
                             hdp_param.HADOOP_DIRECTORY,
                             hdp_param.HADOOP_LOG_DIRECTORY,
                             hdp_param.NODE_USERNAME)
