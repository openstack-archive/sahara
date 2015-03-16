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

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_flume_availability(self, cluster_info):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        self.open_ssh_connection(namenode_ip)
        try:
            self.transfer_helper_script_to_node('flume_service_test.sh')
            self.transfer_helper_conf_file_to_node('flume.data')
            self.transfer_helper_conf_file_to_node('flume.conf')
            self.execute_command('./script.sh')
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(six.text_type(e))
        finally:
            self.close_ssh_connection()

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_sqoop2_availability(self, cluster_info):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        self.open_ssh_connection(namenode_ip)
        try:
            self.transfer_helper_script_to_node('sqoop2_service_test.sh')
            self.execute_command('./script.sh')
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(six.text_type(e))
        finally:
            self.close_ssh_connection()

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_key_value_store_availability(self, cluster_info):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        self.open_ssh_connection(namenode_ip)
        try:
            self.transfer_helper_script_to_node('key_value_store_service'
                                                '_test.sh')
            self.transfer_helper_conf_file_to_node('key_value_store'
                                                   '_indexer.xml')
            self.execute_command('./script.sh create_table -ip %s' %
                                 namenode_ip)
            self.execute_command('./script.sh create_solr_collection -ip %s' %
                                 namenode_ip)
            self.execute_command('./script.sh add_indexer -ip %s' %
                                 namenode_ip)
            self.execute_command('./script.sh create_data -ip %s' %
                                 namenode_ip)
            self.execute_command('./script.sh check_solr -ip %s' %
                                 namenode_ip)
            self.execute_command('./script.sh remove_data -ip %s' %
                                 namenode_ip)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(six.text_type(e))
        finally:
            self.close_ssh_connection()

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_solr_availability(self, cluster_info):
        self._check_service_availability(cluster_info, 'solr_service_test.sh')

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_sentry_availability(self, cluster_info):
        self._check_service_availability(cluster_info,
                                         'sentry_service_test.sh')

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
                parameters = ' '.join(script_parameters)
                script_command = './script.sh %s' % parameters
                self.execute_command(script_command)
            else:
                self.execute_command('./script.sh')
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(six.text_type(e))
        finally:
            self.close_ssh_connection()

    @base.skip_test('SKIP_CHECK_SERVICES_TEST', message='Test for Services'
                    ' checking was skipped.')
    def check_impala_services(self, cluster_info):
        namenode_ip = cluster_info['node_info']['namenode_ip']
        self.open_ssh_connection(namenode_ip)
        try:
            self.transfer_helper_script_to_node('impala_test_script.sh')
            self.execute_command('./script.sh query -ip %s' % namenode_ip)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(six.text_type(e))
        finally:
            self.close_ssh_connection()
