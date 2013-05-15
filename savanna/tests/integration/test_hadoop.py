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

from os import getcwd
import paramiko
from re import search
from savanna.tests.integration.db import ValidationTestCase
from telnetlib import Telnet


def _setup_ssh_connection(host, ssh):
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        host,
        username='root',
        password='swordfish'
    )


def _open_channel_and_execute(ssh, cmd):
    chan = ssh.get_transport().open_session()
    chan.exec_command(cmd)
    return chan.recv_exit_status()


def _execute_command_on_node(host, cmd):
    ssh = paramiko.SSHClient()
    try:
        _setup_ssh_connection(host, ssh)
        return _open_channel_and_execute(ssh, cmd)
    finally:
        ssh.close()


def _execute_transfer_on_node(host, locfile, nodefile):
    try:
        transport = paramiko.Transport(host)
        transport.connect(username='root', password='swordfish')
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(locfile, nodefile)

    finally:
        sftp.close()
        transport.close()


def _execute_transfer_from_node(host, nodefile, localfile):
    try:
        transport = paramiko.Transport(host)
        transport.connect(username='root', password='swordfish')
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get(nodefile, localfile)

    finally:
        sftp.close()
        transport.close()


class TestForHadoop(ValidationTestCase):

    def setUp(self):
        super(TestForHadoop, self).setUp()
        Telnet(self.host, self.port)

    def _hadoop_testing(self, cluster_name, nt_name_master,
                        nt_name_worker, number_workers):
        object_id = None
        cluster_body = self.make_cluster_body(
            cluster_name, nt_name_master, nt_name_worker, number_workers)
        data = self._post_object(self.url_cluster, cluster_body, 202)

        try:
            data = data['cluster']
            object_id = data.pop(u'id')
            get_body = self._get_body_cluster(
                cluster_name, nt_name_master, nt_name_worker, number_workers)
            get_data = self._get_object(self.url_cl_slash, object_id, 200)
            get_data = get_data['cluster']
            del get_data[u'id']
            self._response_cluster(
                get_body, get_data, self.url_cl_slash, object_id)

            get_data = self._get_object(
                self.url_cl_slash, object_id, 200, True)
            get_data = get_data['cluster']
            namenode = get_data[u'service_urls'][u'namenode']
            jobtracker = get_data[u'service_urls'][u'jobtracker']

            p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
            m = search(p, namenode)
            t = search(p, jobtracker)
            namenode_ip = m.group('host')
            namenode_port = m.group('port')
            jobtracker_ip = t.group('host')
            jobtracker_port = t.group('port')

            Telnet(str(namenode_ip), str(namenode_port))
            Telnet(str(jobtracker_ip), str(jobtracker_port))

            this_dir = getcwd()
            _execute_transfer_on_node(
                str(namenode_ip), '%s/integration/script.sh' % this_dir,
                '/script.sh')

            try:
                self.assertEquals(
                    _execute_command_on_node(
                        namenode_ip,
                        "cd .. && chmod 777 script.sh && ./script.sh"), 0)

            except Exception as e:
                _execute_transfer_from_node(
                    namenode_ip, '/outputTestMapReduce/log.txt',
                    '%s' % this_dir)
                self.fail("run script is failure" + e.message)

        except Exception as e:
            self.fail("failure:" + e.message)

        finally:
            self._del_object(self.url_cl_slash, object_id, 204)

    def test_hadoop_single_master(self):
        data_nt_master = self._post_object(
            self.url_nt, self.make_nt('master_node.medium', 'JT+NN',
                                      1234, 2345), 202)
        data_nt_worker = self._post_object(
            self.url_nt, self.make_nt('worker_node.medium', 'TT+DN',
                                      1234, 2345), 202)

        try:
            self._hadoop_testing(
                'QA-hadoop', 'master_node.medium', 'worker_node.medium', 2)

        except Exception as e:
            self.fail("failure:" + str(e))

        finally:
            self.delete_node_template(data_nt_master)
            self.delete_node_template(data_nt_worker)
