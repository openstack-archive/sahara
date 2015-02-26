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

from testtools import testcase

from sahara.tests.integration.configs import config as cfg
from sahara.tests.integration.tests import cinder
from sahara.tests.integration.tests import edp
from sahara.tests.integration.tests import map_reduce
from sahara.tests.integration.tests import scaling
from sahara.tests.integration.tests import swift
from sahara.utils import edp as utils_edp


class HDPGatingTest(cinder.CinderVolumeTest, edp.EDPTest,
                    map_reduce.MapReduceTest, swift.SwiftTest,
                    scaling.ScalingTest):
    config = cfg.ITConfig().hdp_config
    SKIP_CINDER_TEST = config.SKIP_CINDER_TEST
    SKIP_EDP_TEST = config.SKIP_EDP_TEST
    SKIP_MAP_REDUCE_TEST = config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = config.SKIP_SCALING_TEST

    def get_plugin_config(self):
        return cfg.ITConfig().hdp_config

    @testcase.skipIf(config.SKIP_ALL_TESTS_FOR_PLUGIN,
                     'All tests for HDP plugin were skipped')
    @testcase.attr('hdp1')
    def test_hdp_plugin_gating(self):

        # --------------------------CLUSTER CREATION---------------------------

        # ------------------"tt-dn" node group template creation---------------

        node_group_template_tt_dn_id = self.create_node_group_template(
            name='test-node-group-template-hdp-tt-dn',
            plugin_config=self.plugin_config,
            description='test node group template for HDP plugin',
            volumes_per_node=self.volumes_per_node,
            volumes_size=self.volumes_size,
            node_processes=self.plugin_config.WORKER_NODE_PROCESSES,
            node_configs={},
            floating_ip_pool=self.floating_ip_pool,
            auto_security_group=True
        )
        self.addCleanup(self.delete_node_group_template,
                        node_group_template_tt_dn_id)

# --------------------------Cluster template creation--------------------------

        cluster_template_id = self.create_cluster_template(
            name='test-cluster-template-hdp',
            plugin_config=self.plugin_config,
            description='test cluster template for HDP plugin',
            cluster_configs={},
            node_groups=[
                dict(
                    name='master-node-jt-nn',
                    flavor_id=self.flavor_id,
                    node_processes=(
                        self.plugin_config.MASTER_NODE_PROCESSES),
                    node_configs={},
                    floating_ip_pool=self.floating_ip_pool,
                    count=1,
                    auto_security_group=True
                ),
                dict(
                    name='worker-node-tt-dn',
                    node_group_template_id=node_group_template_tt_dn_id,
                    count=3)
            ],
            net_id=self.internal_neutron_net
        )
        self.addCleanup(self.delete_cluster_template, cluster_template_id)

# ------------------------------Cluster creation-------------------------------

        cluster_name = (self.common_config.CLUSTER_NAME + '-' +
                        self.plugin_config.PLUGIN_NAME)

        cluster_id = self.create_cluster(
            name=cluster_name,
            plugin_config=self.plugin_config,
            cluster_template_id=cluster_template_id,
            description='test cluster',
            cluster_configs={}
        )
        self.poll_cluster_state(cluster_id)
        cluster_info = self.get_cluster_info(self.plugin_config)
        self.await_active_workers_for_namenode(cluster_info['node_info'],
                                               self.plugin_config)

        self.addCleanup(self.delete_cluster, self.cluster_id)

# --------------------------------EVENT LOG TESTING---------------------------

        self._test_event_log(cluster_id)

# --------------------------------CINDER TESTING-------------------------------

        self.cinder_volume_testing(cluster_info)

# ---------------------------------EDP TESTING---------------------------------

        pig_job_data = self.edp_info.read_pig_example_script()
        pig_lib_data = self.edp_info.read_pig_example_jar()

        mapreduce_jar_data = self.edp_info.read_mapreduce_example_jar()

        shell_script_data = self.edp_info.read_shell_example_script()
        shell_file_data = self.edp_info.read_shell_example_text_file()

        # This is a modified version of WordCount that takes swift configs
        java_lib_data = self.edp_info.read_java_example_lib()

        job_ids = []
        job_id = self.edp_testing(
            job_type=utils_edp.JOB_TYPE_PIG,
            job_data_list=[{'pig': pig_job_data}],
            lib_data_list=[{'jar': pig_lib_data}],
            swift_binaries=True,
            hdfs_local_output=True)
        job_ids.append(job_id)

        job_id = self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE,
            job_data_list=[],
            lib_data_list=[{'jar': mapreduce_jar_data}],
            configs=self.edp_info.mapreduce_example_configs(),
            swift_binaries=True,
            hdfs_local_output=True)
        job_ids.append(job_id)

        job_id = self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
            job_data_list=[],
            lib_data_list=[],
            configs=self.edp_info.mapreduce_streaming_configs())
        job_ids.append(job_id)

        job_id = self.edp_testing(
            job_type=utils_edp.JOB_TYPE_JAVA,
            job_data_list=[],
            lib_data_list=[{'jar': java_lib_data}],
            configs=self.edp_info.java_example_configs(),
            pass_input_output_args=True)
        job_ids.append(job_id)

        job_id = self.edp_testing(
            job_type=utils_edp.JOB_TYPE_SHELL,
            job_data_list=[{'script': shell_script_data}],
            lib_data_list=[{'text': shell_file_data}],
            configs=self.edp_info.shell_example_configs())
        job_ids.append(job_id)

        self.poll_jobs_status(job_ids)


# -----------------------------MAP REDUCE TESTING------------------------------

        self.map_reduce_testing(cluster_info)

# --------------------------CHECK SWIFT AVAILABILITY---------------------------

        self.check_swift_availability(cluster_info)

# -------------------------------CLUSTER SCALING-------------------------------

        if not self.plugin_config.SKIP_SCALING_TEST:
            datanode_count_after_resizing = (
                cluster_info['node_info']['datanode_count']
                + self.plugin_config.SCALE_EXISTING_NG_COUNT)
            change_list = [
                {
                    'operation': 'resize',
                    'info': ['worker-node-tt-dn',
                             datanode_count_after_resizing]
                },
                {
                    'operation': 'add',
                    'info': [
                        'new-worker-node-tt-dn',
                        self.plugin_config.SCALE_NEW_NG_COUNT,
                        '%s' % node_group_template_tt_dn_id
                    ]
                }
            ]
            new_cluster_info = self.cluster_scaling(cluster_info,
                                                    change_list)
            self.await_active_workers_for_namenode(
                new_cluster_info['node_info'], self.plugin_config)

# --------------------------------EVENT LOG TESTING---------------------------
            self._test_event_log(cluster_id)

# -------------------------CINDER TESTING AFTER SCALING-----------------------

            self.cinder_volume_testing(new_cluster_info)

# ----------------------MAP REDUCE TESTING AFTER SCALING-----------------------

            self.map_reduce_testing(new_cluster_info)

# -------------------CHECK SWIFT AVAILABILITY AFTER SCALING--------------------

            self.check_swift_availability(new_cluster_info)
