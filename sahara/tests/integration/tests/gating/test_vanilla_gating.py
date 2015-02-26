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
from sahara.tests.integration.tests import base as b
from sahara.tests.integration.tests import cinder
from sahara.tests.integration.tests import cluster_configs
from sahara.tests.integration.tests import edp
from sahara.tests.integration.tests import map_reduce
from sahara.tests.integration.tests import scaling
from sahara.tests.integration.tests import swift
from sahara.utils import edp as utils_edp


class VanillaGatingTest(cinder.CinderVolumeTest,
                        cluster_configs.ClusterConfigTest,
                        map_reduce.MapReduceTest, swift.SwiftTest,
                        scaling.ScalingTest, edp.EDPTest):
    config = cfg.ITConfig().vanilla_config
    SKIP_CINDER_TEST = config.SKIP_CINDER_TEST
    SKIP_CLUSTER_CONFIG_TEST = config.SKIP_CLUSTER_CONFIG_TEST
    SKIP_EDP_TEST = config.SKIP_EDP_TEST
    SKIP_MAP_REDUCE_TEST = config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = config.SKIP_SCALING_TEST

    def get_plugin_config(self):
        return cfg.ITConfig().vanilla_config

    @b.errormsg("Failure while 'tt-dn' node group template creation: ")
    def _create_tt_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-vanilla-tt-dn',
            'plugin_config': self.plugin_config,
            'description': 'test node group template for Vanilla 1 plugin',
            'node_processes': ['tasktracker', 'datanode'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {
                'HDFS': cluster_configs.DN_CONFIG,
                'MapReduce': cluster_configs.TT_CONFIG
            }
        }
        self.ng_tmpl_tt_dn_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template, self.ng_tmpl_tt_dn_id)

    @b.errormsg("Failure while 'tt' node group template creation: ")
    def _create_tt_ng_template(self):
        template = {
            'name': 'test-node-group-template-vanilla-tt',
            'plugin_config': self.plugin_config,
            'description': 'test node group template for Vanilla 1 plugin',
            'volumes_per_node': self.volumes_per_node,
            'volumes_size': self.volumes_size,
            'node_processes': ['tasktracker'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {
                'MapReduce': cluster_configs.TT_CONFIG
            }
        }
        self.ng_tmpl_tt_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template, self.ng_tmpl_tt_id)

    @b.errormsg("Failure while 'dn' node group template creation: ")
    def _create_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-vanilla-dn',
            'plugin_config': self.plugin_config,
            'description': 'test node group template for Vanilla 1 plugin',
            'volumes_per_node': self.volumes_per_node,
            'volumes_size': self.volumes_size,
            'node_processes': ['datanode'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {
                'HDFS': cluster_configs.DN_CONFIG
            }
        }
        self.ng_tmpl_dn_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template, self.ng_tmpl_dn_id)

    @b.errormsg("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        template = {
            'name': 'test-cluster-template-vanilla',
            'plugin_config': self.plugin_config,
            'description': 'test cluster template for Vanilla 1 plugin',
            'net_id': self.internal_neutron_net,
            'cluster_configs': {
                'HDFS': cluster_configs.CLUSTER_HDFS_CONFIG,
                'MapReduce': cluster_configs.CLUSTER_MR_CONFIG,
                'general': {
                    'Enable Swift': True
                }
            },
            'node_groups': [
                {
                    'name': 'master-node-jt-nn',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['namenode', 'jobtracker'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'node_configs': {
                        'HDFS': cluster_configs.NN_CONFIG,
                        'MapReduce': cluster_configs.JT_CONFIG
                    },
                    'count': 1
                },
                {
                    'name': 'master-node-sec-nn-oz',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['secondarynamenode', 'oozie'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'node_configs': {
                        'HDFS': cluster_configs.SNN_CONFIG,
                        'JobFlow': cluster_configs.OOZIE_CONFIG
                    },
                    'count': 1
                },
                {
                    'name': 'worker-node-tt-dn',
                    'node_group_template_id': self.ng_tmpl_tt_dn_id,
                    'count': 2
                },
                {
                    'name': 'worker-node-tt',
                    'node_group_template_id': self.ng_tmpl_tt_id,
                    'count': 1
                },
                {
                    'name': 'worker-node-dn',
                    'node_group_template_id': self.ng_tmpl_dn_id,
                    'count': 1
                }
            ]
        }
        self.cluster_template_id = self.create_cluster_template(**template)
        self.addCleanup(self.delete_cluster_template, self.cluster_template_id)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster_name = '%s-%s' % (self.common_config.CLUSTER_NAME,
                                  self.plugin_config.PLUGIN_NAME)
        kw = {
            'name': cluster_name,
            'plugin_config': self.plugin_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {}
        }
        cluster_id = self.create_cluster(**kw)
        self.addCleanup(self.delete_cluster, cluster_id)
        self.poll_cluster_state(cluster_id)
        self.cluster_info = self.get_cluster_info(self.plugin_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg("Failure while Cinder testing: ")
    def _check_cinder(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while cluster config testing: ")
    def _check_cluster_config(self):
        self.cluster_config_testing(self.cluster_info)

    def _run_edp_test(self):
        pig_job_data = self.edp_info.read_pig_example_script()
        pig_lib_data = self.edp_info.read_pig_example_jar()
        mapreduce_jar_data = self.edp_info.read_mapreduce_example_jar()
        # This is a modified version of WordCount that takes swift configs
        java_lib_data = self.edp_info.read_java_example_lib()
        shell_script_data = self.edp_info.read_shell_example_script()
        shell_file_data = self.edp_info.read_shell_example_text_file()

        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_PIG,
            job_data_list=[{'pig': pig_job_data}],
            lib_data_list=[{'jar': pig_lib_data}],
            configs=self.edp_info.pig_example_configs(),
            swift_binaries=True,
            hdfs_local_output=True)

        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE,
            job_data_list=[],
            lib_data_list=[{'jar': mapreduce_jar_data}],
            configs=self.edp_info.mapreduce_example_configs(),
            swift_binaries=True,
            hdfs_local_output=True)

        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
            job_data_list=[],
            lib_data_list=[],
            configs=self.edp_info.mapreduce_streaming_configs())

        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_JAVA,
            job_data_list=[],
            lib_data_list=[{'jar': java_lib_data}],
            configs=self.edp_info.java_example_configs(),
            pass_input_output_args=True)

        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_SHELL,
            job_data_list=[{'script': shell_script_data}],
            lib_data_list=[{'text': shell_file_data}],
            configs=self.edp_info.shell_example_configs())

    @b.errormsg("Failure while EDP testing: ")
    def _check_edp(self):
        self.poll_jobs_status(list(self._run_edp_test()))

    @b.errormsg("Failure while MapReduce testing: ")
    def _check_mapreduce(self):
        self.map_reduce_testing(self.cluster_info)

    @b.errormsg("Failure during check of Swift availability: ")
    def _check_swift(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while cluster scaling: ")
    def _check_scaling(self):
        change_list = [
            {
                'operation': 'resize',
                'info': ['worker-node-tt-dn', 1]
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
                    'new-worker-node-tt', 1, self.ng_tmpl_tt_id
                ]
            },
            {
                'operation': 'add',
                'info': [
                    'new-worker-node-dn', 1, self.ng_tmpl_dn_id
                ]
            }
        ]
        self.cluster_info = self.cluster_scaling(self.cluster_info,
                                                 change_list)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg("Failure while Cinder testing after cluster scaling: ")
    def _check_cinder_after_scaling(self):
        self.cluster_config_testing(self.cluster_info)

    @b.errormsg("Failure while config testing after cluster scaling: ")
    def _check_cluster_config_after_scaling(self):
        self.cluster_config_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing after cluster scaling: ")
    def _check_mapredure_after_scaling(self):
        self.map_reduce_testing(self.cluster_info)

    @b.errormsg("Failure during check of Swift availability after scaling: ")
    def _check_swift_after_scaling(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing after cluster scaling: ")
    def _check_edp_after_scaling(self):
        self.poll_jobs_status(list(self._run_edp_test()))

    @testcase.skipIf(config.SKIP_ALL_TESTS_FOR_PLUGIN,
                     'All tests for Vanilla plugin were skipped')
    @testcase.attr('vanilla1')
    def test_vanilla_plugin_gating(self):
        self._create_tt_dn_ng_template()
        self._create_tt_ng_template()
        self._create_dn_ng_template()
        self._create_cluster_template()
        self._create_cluster()
        self._test_event_log(self.cluster_id)
        self._check_cinder()
        self._check_cluster_config()
        self._check_edp()
        self._check_mapreduce()
        self._check_swift()

        if not self.plugin_config.SKIP_SCALING_TEST:
            self._check_scaling()
            self._test_event_log(self.cluster_id)
            self._check_cinder_after_scaling()
            self._check_cluster_config_after_scaling()
            self._check_mapredure_after_scaling()
            self._check_swift_after_scaling()
            self._check_edp_after_scaling()
