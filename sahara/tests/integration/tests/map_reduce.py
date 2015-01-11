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

from oslo.utils import excutils

from sahara.tests.integration.tests import base


class MapReduceTest(base.ITestCase):
    def _run_pi_job(self):
        self.execute_command('./script.sh run_pi_job')

    def _get_name_of_completed_pi_job(self):
        try:
            job_name = self.execute_command('./script.sh get_pi_job_name')

        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(
                    '\nFailure while name obtaining completed \'PI\' job: ' +
                    str(e)
                )
                self.capture_error_log_from_cluster_node(
                    '/tmp/MapReduceTestOutput/log.txt'
                )
        return job_name[1][:-1]

    def _run_wordcount_job(self):
        try:
            self.execute_command('./script.sh run_wordcount_job')

        except Exception as e:
            with excutils.save_and_reraise_exception():
                print('\nFailure while \'Wordcount\' job launch: ' + str(e))
                self.capture_error_log_from_cluster_node(
                    '/tmp/MapReduceTestOutput/log.txt'
                )

    def _transfer_helper_script_to_nodes(self, cluster_info):
        data = self.sahara.clusters.get(cluster_info['cluster_id'])
        node_groups = data.node_groups
        for node_group in node_groups:
            if node_group['volumes_per_node'] != 0:
                self._add_params_to_script_and_transfer_to_node(
                    cluster_info, node_group, node_with_volumes=True)
            else:
                self._add_params_to_script_and_transfer_to_node(
                    cluster_info, node_group)

    def _add_params_to_script_and_transfer_to_node(self, cluster_info,
                                                   node_group,
                                                   node_with_volumes=False):
        plugin_config = cluster_info['plugin_config']
        hadoop_log_directory = plugin_config.HADOOP_LOG_DIRECTORY
        if node_with_volumes:
            hadoop_log_directory = (
                plugin_config.HADOOP_LOG_DIRECTORY_ON_VOLUME)
        extra_script_parameters = {
            'HADOOP_EXAMPLES_JAR_PATH': plugin_config.HADOOP_EXAMPLES_JAR_PATH,
            'HADOOP_LOG_DIRECTORY': hadoop_log_directory,
            'HADOOP_USER': plugin_config.HADOOP_USER,
            'NODE_COUNT': cluster_info['node_info']['node_count']
        }
        for instance in node_group['instances']:
            try:
                self.open_ssh_connection(instance['management_ip'])
                self.transfer_helper_script_to_node(
                    'map_reduce_test_script.sh', extra_script_parameters
                )
                self.close_ssh_connection()

            except Exception as e:
                with excutils.save_and_reraise_exception():
                    print(str(e))

    @base.skip_test('SKIP_MAP_REDUCE_TEST',
                    message='Test for Map Reduce was skipped.')
    def map_reduce_testing(self, cluster_info, check_log=True):
        self._transfer_helper_script_to_nodes(cluster_info)
        plugin_config = cluster_info['plugin_config']
        namenode_ip = cluster_info['node_info']['namenode_ip']
        self.open_ssh_connection(namenode_ip)
        self._run_pi_job()
        job_name = self._get_name_of_completed_pi_job()
        self.close_ssh_connection()

        # Check that cluster used each "tasktracker" node while work of PI-job.
        # Count of map-tasks and reduce-tasks in helper script guarantees that
        # cluster will use each from such nodes while work of PI-job.
        if check_log:
            node_ip_and_process_list = cluster_info['node_ip_list']

            have_logs = False
            for node_ip, process_list in node_ip_and_process_list.items():
                if plugin_config.PROCESS_NAMES['tt'] in process_list:
                    self.open_ssh_connection(node_ip)
                    try:
                        self.execute_command(
                            './script.sh check_directory -job_name %s' %
                            job_name)
                        have_logs = True
                    except Exception:
                        pass
                    finally:
                        self.close_ssh_connection()

            if not have_logs:
                self.open_ssh_connection(namenode_ip)
                try:
                    self.capture_error_log_from_cluster_node(
                        '/tmp/MapReduceTestOutput/log.txt')
                finally:
                    self.close_ssh_connection()

                self.fail("Log file of completed 'PI' job on 'tasktracker' or "
                          "'nodemanager' cluster node not found.")

        self.open_ssh_connection(namenode_ip)
        self._run_wordcount_job()
        self.close_ssh_connection()
