# Copyright (c) 2014 Mirantis Inc.
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
from sahara.tests.integration.tests import edp
from sahara.tests.integration.tests import scaling
from sahara.tests.integration.tests import swift
from sahara.utils import edp as utils_edp


class HDP2GatingTest(swift.SwiftTest, scaling.ScalingTest,
                     edp.EDPTest):

    config = cfg.ITConfig().hdp2_config
    SKIP_EDP_TEST = config.SKIP_EDP_TEST
    SKIP_SWIFT_TEST = config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = config.SKIP_SCALING_TEST

    def setUp(self):
        super(HDP2GatingTest, self).setUp()
        self.cluster_id = None
        self.cluster_template_id = None
        self.ng_template_ids = []

    def get_plugin_config(self):
        return cfg.ITConfig().hdp2_config

    @b.errormsg("Failure while 'rm-nn' node group template creation: ")
    def _create_rm_nn_ng_template(self):
        template = {
            'name': 'test-node-group-template-hdp2-rm-nn',
            'plugin_config': self.plugin_config,
            'description': 'test node group template for HDP plugin',
            'node_processes': self.plugin_config.MASTER_NODE_PROCESSES,
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_rm_nn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_rm_nn_id)
        self.addCleanup(self.delete_objects,
                        node_group_template_id_list=[self.ng_tmpl_rm_nn_id])

    @b.errormsg("Failure while 'nm-dn' node group template creation: ")
    def _create_nm_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-hdp2-nm-dn',
            'plugin_config': self.plugin_config,
            'description': 'test node group template for HDP plugin',
            'node_processes': self.plugin_config.WORKER_NODE_PROCESSES,
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_nm_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_nm_dn_id)
        self.addCleanup(self.delete_objects,
                        node_group_template_id_list=[self.ng_tmpl_nm_dn_id])

    @b.errormsg("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        template = {
            'name': 'test-cluster-template-hdp2',
            'plugin_config': self.plugin_config,
            'description': 'test cluster template for HDP plugin',
            'cluster_configs': {
                'YARN': {
                    'yarn.log-aggregation-enable': False
                }
            },
            'node_groups': [
                {
                    'name': 'master-node-dn',
                    'node_group_template_id': self.ng_tmpl_rm_nn_id,
                    'count': 1
                },
                {
                    'name': 'worker-node-nm',
                    'node_group_template_id': self.ng_tmpl_nm_dn_id,
                    'count': 3
                }
            ],
            'net_id': self.internal_neutron_net
        }
        self.cluster_template_id = self.create_cluster_template(**template)
        self.addCleanup(self.delete_objects,
                        cluster_template_id=self.cluster_template_id)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster_name = '%s-%s-v2' % (self.common_config.CLUSTER_NAME,
                                     self.plugin_config.PLUGIN_NAME)
        cluster = {
            'name': cluster_name,
            'plugin_config': self.plugin_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {}
        }
        cluster_id = self.create_cluster(**cluster)
        self.addCleanup(self.delete_objects, cluster_id=cluster_id)
        self.poll_cluster_state(cluster_id)
        self.cluster_info = self.get_cluster_info(self.plugin_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg("Failure during check of Swift availability: ")
    def _check_swift(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing: ")
    def _check_edp(self):
        self.poll_jobs_status(list(self._run_edp_test()))

    def _run_edp_test(self):
        # check pig
        pig_job = self.edp_info.read_pig_example_script()
        pig_lib = self.edp_info.read_pig_example_jar()

        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_PIG,
            job_data_list=[{'pig': pig_job}],
            lib_data_list=[{'jar': pig_lib}],
            swift_binaries=True,
            hdfs_local_output=True)

        # check mapreduce
        mapreduce_jar = self.edp_info.read_mapreduce_example_jar()
        mapreduce_configs = self.edp_info.mapreduce_example_configs()
        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE,
            job_data_list=[],
            lib_data_list=[{'jar': mapreduce_jar}],
            configs=mapreduce_configs,
            swift_binaries=True,
            hdfs_local_output=True)

        # check mapreduce streaming
        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
            job_data_list=[],
            lib_data_list=[],
            configs=self.edp_info.mapreduce_streaming_configs())

        # check java
        java_jar = self.edp_info.read_java_example_lib(2)
        java_configs = self.edp_info.java_example_configs(2)
        yield self.edp_testing(
            utils_edp.JOB_TYPE_JAVA,
            job_data_list=[],
            lib_data_list=[{'jar': java_jar}],
            configs=java_configs)

    @b.errormsg("Failure while cluster scaling: ")
    def _check_scaling(self):
        datanode_count_after_resizing = (
            self.cluster_info['node_info']['datanode_count']
            + self.plugin_config.SCALE_EXISTING_NG_COUNT)
        change_list = [
            {
                'operation': 'resize',
                'info': ['worker-node-nm',
                         datanode_count_after_resizing]
            },
            {
                'operation': 'add',
                'info': ['new-worker-node-tt-dn',
                         self.plugin_config.SCALE_NEW_NG_COUNT,
                         '%s' % self.ng_tmpl_nm_dn_id]
            }
        ]

        self.cluster_info = self.cluster_scaling(self.cluster_info,
                                                 change_list)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg(
        "Failure during check of Swift availability after cluster scaling: ")
    def _check_swift_after_scaling(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing after cluster scaling: ")
    def _check_edp_after_scaling(self):
        self._check_edp()

    @testcase.attr('hdp2')
    @testcase.skipIf(config.SKIP_ALL_TESTS_FOR_PLUGIN,
                     'All tests for HDP2 plugin were skipped')
    def test_hdp2_plugin_gating(self):
        self._create_rm_nn_ng_template()
        self._create_nm_dn_ng_template()
        self._create_cluster_template()
        self._create_cluster()

        self._check_swift()
        self._check_edp()

        if not self.plugin_config.SKIP_SCALING_TEST:
            self._check_scaling()
            self._check_swift_after_scaling()
            self._check_edp_after_scaling()

    def tearDown(self):
        super(HDP2GatingTest, self).tearDown()
