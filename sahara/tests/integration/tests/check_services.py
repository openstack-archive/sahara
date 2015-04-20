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

from oslo_utils import excutils
import six

from sahara.tests.integration.tests import base


class CheckServicesTest(base.ITestCase):
    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_hbase_availability(self, cluster_info):
        parameters = ['create_data', 'check_get_data', 'check_delete_data']
        self._check_service_availability(cluster_info, 'hbase_service_test.sh',
                                         script_parameters=parameters,
                                         conf_files=[])

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_flume_availability(self, cluster_info):
        self._check_service_availability(cluster_info, 'flume_service_test.sh',
                                         script_parameters=[],
                                         conf_files=['flume.data',
                                                     'flume.conf'])

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_sqoop2_availability(self, cluster_info):
        self._check_service_availability(cluster_info,
                                         'sqoop2_service_test.sh')

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_key_value_store_availability(self, cluster_info):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        para_create_table = 'create_table -ip %s' % namenode_ip
        para_create_solr = 'create_solr_collection -ip %s' % namenode_ip
        para_add_indexer = 'add_indexer -ip %s' % namenode_ip
        para_create_data = 'create_data -ip %s' % namenode_ip
        para_check_solr = 'check_solr -ip %s' % namenode_ip
        para_remove_data = 'remove_data -ip %s' % namenode_ip
        parameters = [para_create_table, para_create_solr, para_add_indexer,
                      para_create_data, para_check_solr, para_remove_data]
        self._check_service_availability(cluster_info,
                                         'key_value_store_service_test.sh',
                                         script_parameters=parameters,
                                         conf_files=['key_value_'
                                                     'store_indexer.xml'])

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_solr_availability(self, cluster_info):
        self._check_service_availability(cluster_info, 'solr_service_test.sh')

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_sentry_availability(self, cluster_info):
        self._check_service_availability(cluster_info,
                                         'sentry_service_test.sh')

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_impala_services(self, cluster_info):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        parameter = 'query -ip %s' % namenode_ip
        self._check_service_availability(cluster_info, 'impala_test_script.sh',
                                         script_parameters=[parameter],
                                         conf_files=[])

    def _check_service_availability(self, cluster_info, helper_script,
                                    script_parameters=[], conf_files=[]):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        self.open_ssh_connection(namenode_ip)
        try:
            self.transfer_helper_script_to_node(helper_script)
            if conf_files:
                for conf_file in conf_files:
                    self.transfer_helper_conf_file_to_node(conf_file)
            if script_parameters:
                for parameter in script_parameters:
                    script_command = './script.sh %s' % parameter
                    self.execute_command(script_command)
            else:
                self.execute_command('./script.sh')
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(six.text_type(e))
        finally:
            self.close_ssh_connection()
