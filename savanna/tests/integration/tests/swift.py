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

import uuid

from savanna.openstack.common import excutils
from savanna.tests.integration.tests import base


class SwiftTest(base.ITestCase):

    @base.skip_test(
        'SKIP_SWIFT_TEST',
        message='Test for check of Swift availability was skipped.')
    def _check_swift_availability(self, cluster_info):

        plugin_config = cluster_info['plugin_config']

        # Make Swift container id for container uniqueness during Swift testing
        swift_container_id = uuid.uuid4()

        extra_script_parameters = {
            'OS_TENANT_NAME': self.common_config.OS_TENANT_NAME,
            'OS_USERNAME': self.common_config.OS_USERNAME,
            'OS_PASSWORD': self.common_config.OS_PASSWORD,
            'HADOOP_USER': plugin_config.HADOOP_USER,
            'SWIFT_CONTAINER_ID': str(swift_container_id)
        }

        namenode_ip = cluster_info['node_info']['namenode_ip']

        self.open_ssh_connection(namenode_ip, plugin_config.NODE_USERNAME)

        try:

            self.transfer_helper_script_to_node(
                'swift_test_script.sh', parameter_list=extra_script_parameters
            )

        except Exception as e:

            with excutils.save_and_reraise_exception():

                print(str(e))

        swift = self.connect_to_swift()

        swift.put_container('Swift-test-%s' % str(swift_container_id))

        try:

            self.execute_command('./script.sh')

        except Exception as e:

            with excutils.save_and_reraise_exception():

                print(str(e))

        finally:

            self.delete_swift_container(
                swift, 'Swift-test-%s' % str(swift_container_id)
            )

        self.close_ssh_connection()
