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

import os
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
        cl_tmpl_id = None
        cluster_id = None
        try:
            cl_tmpl_body = self.make_cluster_template('cl-tmpl', node_list)
            cl_tmpl_id = self.get_object_id(
                'cluster_template', self.post_object(self.url_cl_tmpl,
                                                     cl_tmpl_body, 202))
            clstr_body = self.make_cl_body_cluster_template(cl_tmpl_id)
            clstr_body['name'] = param.CLUSTER_NAME_HADOOP
            data = self.post_object(self.url_cluster, clstr_body, 202)
            data = data['cluster']
            cluster_id = data.pop('id')
            self.await_cluster_active(self.url_cluster_with_slash, cluster_id)
            time.sleep(30)
            get_data = self.get_object(
                self.url_cluster_with_slash, cluster_id, 200, True)
            get_data = get_data['cluster']
            node_groups = get_data['node_groups']
            ip_instances = {}
            for node_group in node_groups:
                instances = node_group['instances']
                for instans in instances:
                    management_ip = instans['management_ip']
                    ip_instances[management_ip] = node_group[
                        'node_processes']
            namenode_ip = None
            tasktracker_count = 0
            datanode_count = 0
            node_count = 0
            try:
                for key, value in ip_instances.items():
                    telnetlib.Telnet(key, '22')
                    if 'namenode' in value:
                        namenode_ip = key
                        telnetlib.Telnet(key, '50070')
                    if 'tasktracker' in value:
                        tasktracker_count += 1
                        telnetlib.Telnet(key, '50060')
                    if 'datanode' in value:
                        datanode_count += 1
                        telnetlib.Telnet(key, '50075')
                    if 'jobtracker' in value:
                        telnetlib.Telnet(key, '50030')
                    node_count += 1
            except Exception as e:
                self.fail('telnet instances has failure: ' + str(e))
            this_dir = os.getcwd()

            try:
                for key in ip_instances:
                    self.transfer_script_to_node(key, this_dir, 'hadoop_test',
                                                 'hadoop_test_script.sh')
            except Exception as e:
                self.fail('failure in transfer script: ' + str(e))

            self.assertEqual(int(self.execute_command(
                namenode_ip, './script.sh lt -hd %s'
                             % param.HADOOP_DIRECTORY)[1]), tasktracker_count,
                             msg='compare number active trackers is failure: ')
            self.assertEqual(int(self.execute_command(
                namenode_ip, './script.sh ld -hd %s' %
                             param.HADOOP_DIRECTORY)[1]), datanode_count,
                             msg='compare number active datanodes is failure:')

            try:
                self.execute_command(
                    namenode_ip, './script.sh pi -nc %s -hv %s -hd %s'
                                 % (node_count, param.HADOOP_VERSION,
                                    param.HADOOP_DIRECTORY))
            except Exception as e:
                print(self.read_file_from(namenode_ip,
                                          '/tmp/outputTestMapReduce/log.txt'))
                self.fail('run pi script is failure: ' + str(e))

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
            self.del_object(self.url_cl_tmpl_with_slash, cl_tmpl_id, 204)

    def test_hadoop_single_master(self):
        """This test checks hadoop work
        """
        node_list = {self.id_jt_nn: 1, self.id_tt_dn: 1}
        self._hadoop_testing(node_list)

    def tearDown(self):
        self.delete_node_group_templates()
