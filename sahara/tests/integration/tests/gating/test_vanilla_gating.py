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

from sahara.openstack.common import excutils
from sahara.tests.integration.configs import config as cfg
from sahara.tests.integration.tests import cinder
from sahara.tests.integration.tests import cluster_configs
from sahara.tests.integration.tests import map_reduce
from sahara.tests.integration.tests import scaling
from sahara.tests.integration.tests import swift
from sahara.tests.integration.tests import vanilla_transient_cluster
from sahara.utils import edp as utils_edp


class VanillaGatingTest(cinder.CinderVolumeTest,
                        cluster_configs.ClusterConfigTest,
                        map_reduce.MapReduceTest, swift.SwiftTest,
                        scaling.ScalingTest,
                        vanilla_transient_cluster.TransientClusterTest):
    config = cfg.ITConfig().vanilla_config
    SKIP_CINDER_TEST = config.SKIP_CINDER_TEST
    SKIP_CLUSTER_CONFIG_TEST = config.SKIP_CLUSTER_CONFIG_TEST
    SKIP_EDP_TEST = config.SKIP_EDP_TEST
    SKIP_MAP_REDUCE_TEST = config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = config.SKIP_SCALING_TEST
    SKIP_TRANSIENT_CLUSTER_TEST = config.SKIP_TRANSIENT_CLUSTER_TEST

    @testcase.skipIf(config.SKIP_ALL_TESTS_FOR_PLUGIN,
                     'All tests for Vanilla plugin were skipped')
    @testcase.attr('vanilla1', 'transient')
    def test_vanilla_plugin_gating(self):
        self.vanilla_config.IMAGE_ID, self.vanilla_config.SSH_USERNAME = (
            self.get_image_id_and_ssh_username(self.vanilla_config))

        # Default value of self.common_config.FLOATING_IP_POOL is None
        floating_ip_pool = self.common_config.FLOATING_IP_POOL
        internal_neutron_net = None
        # If Neutron enabled then get ID of floating IP pool and ID of internal
        # Neutron network
        if self.common_config.NEUTRON_ENABLED:
            floating_ip_pool = self.get_floating_ip_pool_id_for_neutron_net()
            internal_neutron_net = self.get_internal_neutron_net_id()

# ---------------------------TRANSIENT CLUSTER TESTING-------------------------

        try:
            self.transient_cluster_testing(
                self.vanilla_config, floating_ip_pool, internal_neutron_net)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                message = 'Failure while transient cluster testing: '
                self.print_error_log(message, e)

        if self.vanilla_config.ONLY_TRANSIENT_CLUSTER_TEST:
            return

# ------------------------------CLUSTER CREATION-------------------------------

# --------------------"tt-dn" node group template creation---------------------

        node_group_template_id_list = []

        try:
            node_group_template_tt_dn_id = self.create_node_group_template(
                name='test-node-group-template-vanilla-tt-dn',
                plugin_config=self.vanilla_config,
                description='test node group template for Vanilla plugin',
                node_processes=['tasktracker', 'datanode'],
                node_configs={
                    'HDFS': cluster_configs.DN_CONFIG,
                    'MapReduce': cluster_configs.TT_CONFIG
                },
                floating_ip_pool=floating_ip_pool
            )
            node_group_template_id_list.append(node_group_template_tt_dn_id)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                message = ('Failure while \'tt-dn\' node group '
                           'template creation: ')
                self.print_error_log(message, e)

# ----------------------"tt" node group template creation----------------------

        if not self.vanilla_config.SKIP_CINDER_TEST:
            volumes_per_node = 2
            volume_size = 2
        else:
            volumes_per_node = 0
            volume_size = 0

        try:
            node_group_template_tt_id = self.create_node_group_template(
                name='test-node-group-template-vanilla-tt',
                plugin_config=self.vanilla_config,
                description='test node group template for Vanilla plugin',
                volumes_per_node=volumes_per_node,
                volume_size=volume_size,
                node_processes=['tasktracker'],
                node_configs={
                    'MapReduce': cluster_configs.TT_CONFIG
                },
                floating_ip_pool=floating_ip_pool
            )
            node_group_template_id_list.append(node_group_template_tt_id)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    node_group_template_id_list=node_group_template_id_list
                )
                message = 'Failure while \'tt\' node group template creation: '
                self.print_error_log(message, e)

# ---------------------"dn" node group template creation-----------------------

        try:
            node_group_template_dn_id = self.create_node_group_template(
                name='test-node-group-template-vanilla-dn',
                plugin_config=self.vanilla_config,
                description='test node group template for Vanilla plugin',
                volumes_per_node=volumes_per_node,
                volume_size=volume_size,
                node_processes=['datanode'],
                node_configs={
                    'HDFS': cluster_configs.DN_CONFIG
                },
                floating_ip_pool=floating_ip_pool
            )
            node_group_template_id_list.append(node_group_template_dn_id)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    node_group_template_id_list=node_group_template_id_list
                )
                message = 'Failure while \'dn\' node group template creation: '
                self.print_error_log(message, e)

# --------------------------Cluster template creation--------------------------

        try:
            cluster_template_id = self.create_cluster_template(
                name='test-cluster-template-vanilla',
                plugin_config=self.vanilla_config,
                description='test cluster template for Vanilla plugin',
                cluster_configs={
                    'HDFS': cluster_configs.CLUSTER_HDFS_CONFIG,
                    'MapReduce': cluster_configs.CLUSTER_MR_CONFIG,
                    'general': {'Enable Swift': True}
                },
                node_groups=[
                    dict(
                        name='master-node-jt-nn',
                        flavor_id=self.flavor_id,
                        node_processes=['namenode', 'jobtracker'],
                        node_configs={
                            'HDFS': cluster_configs.NN_CONFIG,
                            'MapReduce': cluster_configs.JT_CONFIG
                        },
                        floating_ip_pool=floating_ip_pool,
                        count=1),
                    dict(
                        name='master-node-sec-nn-oz',
                        flavor_id=self.flavor_id,
                        node_processes=['secondarynamenode', 'oozie'],
                        node_configs={
                            'HDFS': cluster_configs.SNN_CONFIG,
                            'JobFlow': cluster_configs.OOZIE_CONFIG
                        },
                        floating_ip_pool=floating_ip_pool,
                        count=1),
                    dict(
                        name='worker-node-tt-dn',
                        node_group_template_id=node_group_template_tt_dn_id,
                        count=3),
                    dict(
                        name='worker-node-dn',
                        node_group_template_id=node_group_template_dn_id,
                        count=1),
                    dict(
                        name='worker-node-tt',
                        node_group_template_id=node_group_template_tt_id,
                        count=1)
                ],
                net_id=internal_neutron_net
            )

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    node_group_template_id_list=node_group_template_id_list
                )
                message = 'Failure while cluster template creation: '
                self.print_error_log(message, e)

# ------------------------------Cluster creation-------------------------------

        try:
            cluster_name = "%s-%s-v1" % (self.common_config.CLUSTER_NAME,
                                         self.vanilla_config.PLUGIN_NAME)
            self.create_cluster(
                name=cluster_name,
                plugin_config=self.vanilla_config,
                cluster_template_id=cluster_template_id,
                description='test cluster',
                cluster_configs={}
            )

            cluster_info = self.get_cluster_info(self.vanilla_config)
            self.await_active_workers_for_namenode(cluster_info['node_info'],
                                                   self.vanilla_config)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    self.cluster_id, cluster_template_id,
                    node_group_template_id_list
                )
                message = 'Failure while cluster creation: '
                self.print_error_log(message, e)

# --------------------------------CINDER TESTING-------------------------------

        try:
            self.cinder_volume_testing(cluster_info)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )
                message = 'Failure while Cinder testing: '
                self.print_error_log(message, e)

# ---------------------------CLUSTER CONFIG TESTING----------------------------

        try:
            self.cluster_config_testing(cluster_info)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )
                message = 'Failure while cluster config testing: '
                self.print_error_log(message, e)

# ---------------------------------EDP TESTING---------------------------------

        path = 'sahara/tests/integration/tests/resources/'
        pig_job_data = open(path + 'edp-job.pig').read()
        pig_lib_data = open(path + 'edp-lib.jar').read()
        mapreduce_jar_data = open(path + 'edp-mapreduce.jar').read()

        # This is a modified version of WordCount that takes swift configs
        java_lib_data = open(path + 'edp-java/edp-java.jar').read()
        java_configs = {
            "configs": {
                "edp.java.main_class":
                    "org.openstack.sahara.examples.WordCount"
            }
        }

        mapreduce_configs = {
            "configs": {
                "mapred.mapper.class":
                    "org.apache.oozie.example.SampleMapper",
                "mapred.reducer.class":
                    "org.apache.oozie.example.SampleReducer"
            }
        }
        mapreduce_streaming_configs = {
            "configs": {
                "edp.streaming.mapper": "/bin/cat",
                "edp.streaming.reducer": "/usr/bin/wc"
            }
        }
        try:
            self.edp_testing(job_type=utils_edp.JOB_TYPE_PIG,
                             job_data_list=[{'pig': pig_job_data}],
                             lib_data_list=[{'jar': pig_lib_data}],
                             swift_binaries=True,
                             hdfs_local_output=True)
            self.edp_testing(job_type=utils_edp.JOB_TYPE_MAPREDUCE,
                             job_data_list=[],
                             lib_data_list=[{'jar': mapreduce_jar_data}],
                             configs=mapreduce_configs,
                             swift_binaries=True,
                             hdfs_local_output=True)
            self.edp_testing(job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
                             job_data_list=[],
                             lib_data_list=[],
                             configs=mapreduce_streaming_configs)
            self.edp_testing(job_type=utils_edp.JOB_TYPE_JAVA,
                             job_data_list=[],
                             lib_data_list=[{'jar': java_lib_data}],
                             configs=java_configs,
                             pass_input_output_args=True)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )
                message = 'Failure while EDP testing: '
                self.print_error_log(message, e)

# -----------------------------MAP REDUCE TESTING------------------------------

        try:
            self.map_reduce_testing(cluster_info)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )
                message = 'Failure while Map Reduce testing: '
                self.print_error_log(message, e)

# --------------------------CHECK SWIFT AVAILABILITY---------------------------

        try:
            self.check_swift_availability(cluster_info)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )
                message = 'Failure during check of Swift availability: '
                self.print_error_log(message, e)

# -------------------------------CLUSTER SCALING-------------------------------

        if not self.vanilla_config.SKIP_SCALING_TEST:
            change_list = [
                {
                    'operation': 'resize',
                    'info': ['worker-node-tt-dn', 4]
                },
                {
                    'operation': 'resize',
                    'info': ['worker-node-dn', 0]
                },
                {
                    'operation': 'resize',
                    'info': ['worker-node-tt', 0]
                },
                {
                    'operation': 'add',
                    'info': [
                        'new-worker-node-tt', 1, node_group_template_tt_id
                    ]
                },
                {
                    'operation': 'add',
                    'info': [
                        'new-worker-node-dn', 1, node_group_template_dn_id
                    ]
                }
            ]
            try:
                new_cluster_info = self.cluster_scaling(cluster_info,
                                                        change_list)
                self.await_active_workers_for_namenode(
                    new_cluster_info['node_info'], self.vanilla_config)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.delete_objects(
                        cluster_info['cluster_id'], cluster_template_id,
                        node_group_template_id_list
                    )
                    message = 'Failure while cluster scaling: '
                    self.print_error_log(message, e)

# -------------------------CINDER TESTING AFTER SCALING------------------------

            try:
                self.cinder_volume_testing(new_cluster_info)

            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.delete_objects(
                        new_cluster_info['cluster_id'], cluster_template_id,
                        node_group_template_id_list
                    )
                    message = ('Failure while Cinder testing after cluster '
                               'scaling: ')
                    self.print_error_log(message, e)

# --------------------CLUSTER CONFIG TESTING AFTER SCALING---------------------

            try:
                self.cluster_config_testing(new_cluster_info)

            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.delete_objects(
                        new_cluster_info['cluster_id'], cluster_template_id,
                        node_group_template_id_list
                    )
                    message = ('Failure while cluster config testing after '
                               'cluster scaling: ')
                    self.print_error_log(message, e)

# ----------------------MAP REDUCE TESTING AFTER SCALING-----------------------

            try:
                self.map_reduce_testing(new_cluster_info)

            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.delete_objects(
                        new_cluster_info['cluster_id'], cluster_template_id,
                        node_group_template_id_list
                    )
                    message = ('Failure while Map Reduce testing after '
                               'cluster scaling: ')
                    self.print_error_log(message, e)

# -------------------CHECK SWIFT AVAILABILITY AFTER SCALING--------------------

            try:
                self.check_swift_availability(new_cluster_info)

            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.delete_objects(
                        new_cluster_info['cluster_id'], cluster_template_id,
                        node_group_template_id_list
                    )
                    message = ('Failure during check of Swift availability '
                               'after cluster scaling: ')
                    self.print_error_log(message, e)

# ---------------------------DELETE CREATED OBJECTS----------------------------

        self.delete_objects(
            cluster_info['cluster_id'], cluster_template_id,
            node_group_template_id_list
        )
