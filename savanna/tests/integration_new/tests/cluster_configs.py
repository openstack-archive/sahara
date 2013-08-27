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


#TODO(ylobankov): add secondary nn config when bug #1217245 will be fixed
NN_CONFIG = {'Name Node Heap Size': 512}
JT_CONFIG = {'Job Tracker Heap Size': 514}

DN_CONFIG = {'Data Node Heap Size': 513}
TT_CONFIG = {'Task Tracker Heap Size': 515}

CLUSTER_GENERAL_CONFIG = {'Enable Swift': True}
CLUSTER_HDFS_CONFIG = {'dfs.replication': 2}
CLUSTER_MR_CONFIG = {'mapred.map.tasks.speculative.execution': False,
                     'mapred.child.java.opts': '-Xmx500m'}

CONFIG_MAP = {
    'namenode': {
        'service': 'HDFS',
        'config': NN_CONFIG
    },
    'jobtracker': {
        'service': 'MapReduce',
        'config': JT_CONFIG
    },
    'datanode': {
        'service': 'HDFS',
        'config': DN_CONFIG
    },
    'tasktracker': {
        'service': 'MapReduce',
        'config': TT_CONFIG
    }
}


class ClusterConfigTest(base.ITestCase):

    def __get_node_configs(self, node_group, process):

        return node_group['node_configs'][CONFIG_MAP[process]['service']]

    def __get_config_from_config_map(self, process):

        return CONFIG_MAP[process]['config']

    def __compare_configs(self, obtained_config, config):

        self.assertEqual(
            obtained_config, config,
            'Failure while config comparison: configs are not equal. \n'
            'Config obtained with \'get\'-request: %s. \n'
            'Config while cluster creation: %s.'
            % (str(obtained_config), str(config))
        )

    def __compare_configs_on_cluster_node(self, config, value):

        config = config.replace(' ', '')

        try:

            self.execute_command('./script.sh %s -value %s' % (config, value))

        except Exception as e:

            with excutils.save_and_reraise_exception():

                print(
                    'Failure while config comparison on cluster node: '
                    + str(e)
                )
                print(
                    self.read_file_from('/tmp/config-test-log.txt')
                )

    def __check_configs_for_node_groups(self, node_groups):

        for node_group in node_groups:

            for process in node_group['node_processes']:

                if process in CONFIG_MAP:

                    self.__compare_configs(
                        self.__get_node_configs(node_group, process),
                        self.__get_config_from_config_map(process)
                    )

    def __check_config_application_on_cluster_nodes(
            self, node_ip_list_with_node_processes):

        for node_ip, processes in node_ip_list_with_node_processes.items():

            self.open_ssh_connection(node_ip, self.VANILLA.NODE_USERNAME)

            for config, value in CLUSTER_MR_CONFIG.items():

                self.__compare_configs_on_cluster_node(config, value)

            for config, value in CLUSTER_HDFS_CONFIG.items():

                self.__compare_configs_on_cluster_node(config, value)

            if 'namenode' in processes:

                swift = swift_client.Connection(
                    authurl=self.COMMON.OS_AUTH_URL,
                    user=self.COMMON.OS_USERNAME,
                    key=self.COMMON.OS_PASSWORD,
                    tenant_name=self.COMMON.OS_TENANT_NAME,
                    auth_version='2')  # TODO(ylobankov): delete hard code

                swift.put_container('Swift-config-test')

                try:

                    for config, value in CLUSTER_GENERAL_CONFIG.items():

                        self.__compare_configs_on_cluster_node(config, value)

                finally:

                    self.delete_swift_container(swift, 'Swift-config-test')

#TODO(ylobankov): add check for secondary nn when bug #1217245 will be fixed
            for process in processes:

                if process in CONFIG_MAP:

                    for config, value in self.__get_config_from_config_map(
                            process).items():

                        self.__compare_configs_on_cluster_node(config, value)

            self.close_ssh_connection()

    @base.skip_test('SKIP_CLUSTER_CONFIG_TEST',
                    message='Test for cluster configs was skipped.')
    def _cluster_config_testing(self, cluster_info):

        cluster_id = cluster_info['cluster_id']
        data = self.savanna.clusters.get(cluster_id)

        self.__compare_configs(
            data.cluster_configs['general'], CLUSTER_GENERAL_CONFIG
        )
        self.__compare_configs(
            data.cluster_configs['HDFS'], CLUSTER_HDFS_CONFIG
        )
        self.__compare_configs(
            data.cluster_configs['MapReduce'], CLUSTER_MR_CONFIG
        )

        node_groups = data.node_groups

        self.__check_configs_for_node_groups(node_groups)

        node_ip_list_with_node_processes = \
            self.get_cluster_node_ip_list_with_node_processes(cluster_id)

        extra_script_parameters = {
            'OS_TENANT_NAME': self.COMMON.OS_TENANT_NAME,
            'OS_USERNAME': self.COMMON.OS_USERNAME,
            'OS_PASSWORD': self.COMMON.OS_PASSWORD,
            'HADOOP_USER': self.VANILLA.HADOOP_USER
        }

        try:

            self.transfer_helper_script_to_nodes(
                node_ip_list_with_node_processes, self.VANILLA.NODE_USERNAME,
                'cluster_config_test_script.sh', extra_script_parameters
            )

        except Exception as e:

            with excutils.save_and_reraise_exception():

                print(str(e))

        self.__check_config_application_on_cluster_nodes(
            node_ip_list_with_node_processes
        )
