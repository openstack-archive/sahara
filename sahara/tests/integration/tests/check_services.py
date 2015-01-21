# Copyright (c) 2015 Intel Corporation.
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

from oslo.utils import excutils

from sahara.tests.integration.tests import base


class CheckServicesTest(base.ITestCase):
    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_hbase_availability(self, cluster_info):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        self.open_ssh_connection(namenode_ip)
        try:
            self.transfer_helper_script_to_node('hbase_service_test.sh')
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(str(e))
        try:
            self.execute_command('./script.sh create_data')
            self.execute_command('./script.sh check_get_data')
            self.execute_command('./script.sh check_delete_data')
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(str(e))
        finally:
            self.close_ssh_connection()
