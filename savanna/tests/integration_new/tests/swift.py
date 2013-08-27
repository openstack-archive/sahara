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


from swiftclient import client as swift_client


from savanna.openstack.common import excutils
from savanna.tests.integration_new.tests import base


class SwiftTest(base.ITestCase):

    @base.skip_test(
        'SKIP_SWIFT_TEST',
        message='Test for check of Swift availability was skipped.')
    def _check_swift_availability(self, cluster_info):

        plugin = cluster_info['plugin']

        extra_script_parameters = {
            'OS_TENANT_NAME': self.COMMON.OS_TENANT_NAME,
            'OS_USERNAME': self.COMMON.OS_USERNAME,
            'OS_PASSWORD': self.COMMON.OS_PASSWORD,
            'HADOOP_USER': plugin.HADOOP_USER,
        }

        namenode_ip = cluster_info['node_info']['namenode_ip']

        self.open_ssh_connection(namenode_ip, plugin.NODE_USERNAME)

        try:

            self.transfer_helper_script_to_node('swift_test_script.sh',
                                                extra_script_parameters)

        except Exception as e:

            with excutils.save_and_reraise_exception():

                print(str(e))

        swift = swift_client.Connection(
            authurl=self.COMMON.OS_AUTH_URL,
            user=self.COMMON.OS_USERNAME,
            key=self.COMMON.OS_PASSWORD,
            tenant_name=self.COMMON.OS_TENANT_NAME,
            auth_version='2')  # TODO(ylobankov): delete hard code

        swift.put_container('Swift-test')

        try:

            self.execute_command('./script.sh')

        except Exception as e:

            with excutils.save_and_reraise_exception():

                print(str(e))

        finally:

            self.delete_swift_container(swift, 'Swift-test')

        self.close_ssh_connection()
