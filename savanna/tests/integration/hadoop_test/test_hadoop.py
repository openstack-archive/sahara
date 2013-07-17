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
import time

from savanna.tests.integration import base
import savanna.tests.integration.configs.parameters as param


class TestHadoop(base.ITestCase):

    def setUp(self):
        super(TestHadoop, self).setUp()
        telnetlib.Telnet(self.host, self.port)
        self.create_node_group_templates()

    def _hadoop_testing(self, node_list):
        cluster_id = None
        try:
            cluster_id = self.create_cluster_using_ngt_and_get_id(
                node_list, param.CLUSTER_NAME_HADOOP)
            ip_instances = self.get_instances_ip_and_node_processes_list(
                cluster_id)
            namenode_ip = None
            node_count = 0
            try:
                clstr_info = self.get_namenode_ip_and_tt_dn_count(ip_instances)
                namenode_ip = clstr_info['namenode_ip']
                node_count = clstr_info['node_count']
                self.await_active_workers_for_namenode(clstr_info)
            except Exception as e:
                self.fail(str(e))
            try:
                for key in ip_instances:
                    self.transfer_script_to_node(key)
            except Exception as e:
                self.fail('failure in transfer script: ' + str(e))
            try:
                self.execute_command(
                    namenode_ip, './script.sh pi -nc %s -hv %s -hd %s'
                                 % (node_count, param.HADOOP_VERSION,
                                    param.HADOOP_DIRECTORY))
            except Exception as e:
                print(self.read_file_from(namenode_ip,
                                          '/tmp/outputTestMapReduce/log.txt'))
                self.fail(
                    'run pi script has failed: '
                    + str(e))
            try:
                job_name = self.execute_command(
                    namenode_ip, './script.sh gn -hd %s'
                                 % param.HADOOP_DIRECTORY)[1]
                if job_name == 'JobId':
                    self.fail()
            except Exception as e:
                self.fail('fail in get job name: ' + str(e))

            for key, value in ip_instances.items():
                if 'datanode' in value or 'tasktracker' in value:
                    self.assertEquals(
                        self.execute_command(
                            key, './script.sh ed -jn %s -hld %s'
                                 % (job_name[:-1],
                                    param.HADOOP_LOG_DIRECTORY))[0], 0,
                        msg='fail in check run job in worker nodes: ')

            try:
                self.assertEquals(
                    self.execute_command(
                        namenode_ip, './script.sh mr -hv %s -hd %s'
                                     % (param.HADOOP_VERSION,
                                        param.HADOOP_DIRECTORY))[0], 0)
            except Exception as e:
                print(self.read_file_from(namenode_ip,
                                          '/tmp/outputTestMapReduce/log.txt'))
                self.fail('run hdfs script is failure: ' + str(e))
        except Exception as e:
            self.fail(str(e))

        finally:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            time.sleep(5)

    def test_hadoop_single_master(self):
        """This test checks hadoop work
        """
        node_list = {self.id_jt_nn: 1, self.id_tt_dn: 1}
        self._hadoop_testing(node_list)

    def tearDown(self):
        self.delete_node_group_templates()
