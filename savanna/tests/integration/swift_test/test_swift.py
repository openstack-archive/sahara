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


@base.swift_test
class SwiftTest(base.ITestCase):

    def setUp(self):
        super(SwiftTest, self).setUp()

        telnetlib.Telnet(self.host, self.port)

    def _check_availability_swift_cluster(self, data):
        this_dir = os.getcwd()

        self.execute_command(data['namenode_ip'], 'sudo mkdir /tmp/swift && \
        sudo chmod -R 777 /tmp/swift ')

        self.write_file_to(data['namenode_ip'],
                           '/tmp/swift/generate_job_file.py',
                           open(
                               '%s/integration/swift_test/generate_job_file.py'
                               % this_dir).read())

        self.execute_command(data['namenode_ip'],
                             'python /tmp/swift/generate_job_file.py && \
                        sudo apt-get install -y python-pip && \
                        sudo pip install python-swiftclient && \
                        sudo pip install python-keystoneclient && \
                        export ST_AUTH=%s && \
                        export ST_USER=%s:admin && \
                        export ST_KEY=%s && \
                        swift -V2.0 post hadoop-job-files && \
                        swift -V2.0 upload hadoop-job-files \
                        hadoop-job-file.txt && \
                        sudo su -c "hadoop distcp -D \
                        fs.swift.service.savanna.username=%s -D \
                        fs.swift.service.savanna.password=%s \
        swift://hadoop-job-files.savanna/hadoop-job-file.txt /" hadoop && \
                        swift -V2.0 delete hadoop-job-files && \
                        hadoop dfs -copyToLocal /hadoop-job-file.txt \
                        /home/%s/hadoop-job-swift-file.txt'
                             % (param.OS_AUTH_URL,
                                param.OS_TENANT_NAME,
                                param.OS_PASSWORD,
                                param.OS_USERNAME,
                                param.OS_PASSWORD,
                                param.NODE_USERNAME))

        self.assertEquals(
            self.execute_command(
                data['namenode_ip'], 'diff hadoop-job-swift-file.txt \
                hadoop-job-file.txt')[0], 0,
            'hadoop-job-swift-file.txt != hadoop-job-file.txt')

    def test_swift(self):
        """This test checks swift work
        """
        node_processes = {'JT+NN': 1, 'TT+DN': 2}

        cluster_body = self.make_cl_body_node_processes(node_processes)
        cluster_body['name'] = param.CLUSTER_NAME_SWIFT

        try:
            cluster_id = self.create_cluster_and_get_id(cluster_body)

            instances_ip = self.get_instances_ip_and_node_processes_list(
                cluster_id)

            time.sleep(10)

            data = self.get_namenode_ip_and_tt_dn_count(instances_ip)

            self.await_active_workers_for_namenode(data)

            self._check_availability_swift_cluster(data)

        finally:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
