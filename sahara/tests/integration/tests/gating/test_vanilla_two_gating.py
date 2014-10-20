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
from sahara.tests.integration.tests import cinder
from sahara.tests.integration.tests import cluster_configs
from sahara.tests.integration.tests import edp
from sahara.tests.integration.tests import map_reduce
from sahara.tests.integration.tests import scaling
from sahara.tests.integration.tests import swift
from sahara.utils import edp as utils_edp


class VanillaTwoGatingTest(cluster_configs.ClusterConfigTest,
                           map_reduce.MapReduceTest, swift.SwiftTest,
                           scaling.ScalingTest, cinder.CinderVolumeTest,
                           edp.EDPTest):

    vanilla_two_config = cfg.ITConfig().vanilla_two_config
    SKIP_MAP_REDUCE_TEST = vanilla_two_config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = vanilla_two_config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = vanilla_two_config.SKIP_SCALING_TEST
    SKIP_CINDER_TEST = vanilla_two_config.SKIP_CINDER_TEST
    SKIP_EDP_TEST = vanilla_two_config.SKIP_EDP_TEST

    def setUp(self):
        super(VanillaTwoGatingTest, self).setUp()
        self.cluster_id = None
        self.cluster_template_id = None
        self.ng_template_ids = []

    def _prepare_test(self):
        self.vanilla_two_config = cfg.ITConfig().vanilla_two_config
        self.floating_ip_pool = self.common_config.FLOATING_IP_POOL
        self.internal_neutron_net = None
        if self.common_config.NEUTRON_ENABLED:
            self.internal_neutron_net = self.get_internal_neutron_net_id()
            self.floating_ip_pool = (
                self.get_floating_ip_pool_id_for_neutron_net())

        (self.vanilla_two_config.IMAGE_ID,
         self.vanilla_two_config.SSH_USERNAME) = (
            self.get_image_id_and_ssh_username(self.vanilla_two_config))

        self.volumes_per_node = 0
        self.volumes_size = 0
        if not self.SKIP_CINDER_TEST:
            self.volumes_per_node = 2
            self.volumes_size = 2

    ng_params = {
        'MapReduce': {
            'yarn.app.mapreduce.am.resource.mb': 256,
            'yarn.app.mapreduce.am.command-opts': '-Xmx256m'
        },
        'YARN': {
            'yarn.scheduler.minimum-allocation-mb': 256,
            'yarn.scheduler.maximum-allocation-mb': 1024,
            'yarn.nodemanager.vmem-check-enabled': False
        }
    }

    @b.errormsg("Failure while 'nm-dn' node group template creation: ")
    def _create_nm_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-vanilla-nm-dn',
            'plugin_config': self.vanilla_two_config,
            'description': 'test node group template for Vanilla plugin',
            'node_processes': ['nodemanager', 'datanode'],
            'floating_ip_pool': self.floating_ip_pool,
            'node_configs': self.ng_params
        }
        self.ng_tmpl_nm_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_nm_dn_id)

    @b.errormsg("Failure while 'nm' node group template creation: ")
    def _create_nm_ng_template(self):
        template = {
            'name': 'test-node-group-template-vanilla-nm',
            'plugin_config': self.vanilla_two_config,
            'description': 'test node group template for Vanilla plugin',
            'volumes_per_node': self.volumes_per_node,
            'volumes_size': self.volumes_size,
            'node_processes': ['nodemanager'],
            'floating_ip_pool': self.floating_ip_pool,
            'node_configs': self.ng_params
        }
        self.ng_tmpl_nm_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_nm_id)

    @b.errormsg("Failure while 'dn' node group template creation: ")
    def _create_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-vanilla-dn',
            'plugin_config': self.vanilla_two_config,
            'description': 'test node group template for Vanilla plugin',
            'volumes_per_node': self.volumes_per_node,
            'volumes_size': self.volumes_size,
            'node_processes': ['datanode'],
            'floating_ip_pool': self.floating_ip_pool,
            'node_configs': self.ng_params
        }
        self.ng_tmpl_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_dn_id)

    @b.errormsg("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        template = {
            'name': 'test-cluster-template-vanilla',
            'plugin_config': self.vanilla_two_config,
            'description': 'test cluster template for Vanilla plugin',
            'cluster_configs': {
                'HDFS': {
                    'dfs.replication': 1
                }
            },
            'node_groups': [
                {
                    'name': 'master-node-rm-nn',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['namenode', 'resourcemanager'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'count': 1,
                    'node_configs': self.ng_params
                },
                {
                    'name': 'master-node-oo-hs',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['oozie', 'historyserver',
                                       'secondarynamenode'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'count': 1,
                    'node_configs': self.ng_params
                },
                {
                    'name': 'worker-node-nm-dn',
                    'node_group_template_id': self.ng_tmpl_nm_dn_id,
                    'count': 2
                },
                {
                    'name': 'worker-node-dn',
                    'node_group_template_id': self.ng_tmpl_dn_id,
                    'count': 1
                },
                {
                    'name': 'worker-node-nm',
                    'node_group_template_id': self.ng_tmpl_nm_id,
                    'count': 1
                }
            ],
            'net_id': self.internal_neutron_net
        }
        self.cluster_template_id = self.create_cluster_template(**template)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster_name = '%s-%s-v2' % (self.common_config.CLUSTER_NAME,
                                     self.vanilla_two_config.PLUGIN_NAME)
        cluster = {
            'name': cluster_name,
            'plugin_config': self.vanilla_two_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {}
        }
        cluster_id = self.create_cluster(**cluster)
        self.poll_cluster_state(cluster_id)
        self.cluster_info = self.get_cluster_info(self.vanilla_two_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.vanilla_two_config)

    @b.errormsg("Failure while Cinder testing: ")
    def _check_cinder(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing: ")
    def _check_mapreduce(self):
        self.map_reduce_testing(self.cluster_info)

    @b.errormsg("Failure during check of Swift availability: ")
    def _check_swift(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing: ")
    def _check_edp(self):
        self.poll_jobs_status(list(self._run_edp_tests()))

    def _run_edp_tests(self):
        skipped_edp_job_types = self.vanilla_two_config.SKIP_EDP_JOB_TYPES

        if utils_edp.JOB_TYPE_PIG not in skipped_edp_job_types:
            yield self._edp_pig_test()
        if utils_edp.JOB_TYPE_MAPREDUCE not in skipped_edp_job_types:
            yield self._edp_mapreduce_test()
        if utils_edp.JOB_TYPE_MAPREDUCE_STREAMING not in skipped_edp_job_types:
            yield self._edp_mapreduce_streaming_test()
        if utils_edp.JOB_TYPE_JAVA not in skipped_edp_job_types:
            yield self._edp_java_test()

    def _edp_pig_test(self):
        pig_job = self.edp_info.read_pig_example_script()
        pig_lib = self.edp_info.read_pig_example_jar()

        return self.edp_testing(
            job_type=utils_edp.JOB_TYPE_PIG,
            job_data_list=[{'pig': pig_job}],
            lib_data_list=[{'jar': pig_lib}],
            swift_binaries=True,
            hdfs_local_output=True)

    def _edp_mapreduce_test(self):
        mapreduce_jar = self.edp_info.read_mapreduce_example_jar()
        mapreduce_configs = self.edp_info.mapreduce_example_configs()
        return self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE,
            job_data_list=[],
            lib_data_list=[{'jar': mapreduce_jar}],
            configs=mapreduce_configs,
            swift_binaries=True,
            hdfs_local_output=True)

    def _edp_mapreduce_streaming_test(self):
        return self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
            job_data_list=[],
            lib_data_list=[],
            configs=self.edp_info.mapreduce_streaming_configs())

    def _edp_java_test(self):
        java_jar = self.edp_info.read_java_example_lib(2)
        java_configs = self.edp_info.java_example_configs(2)
        return self.edp_testing(
            utils_edp.JOB_TYPE_JAVA,
            job_data_list=[],
            lib_data_list=[{'jar': java_jar}],
            configs=java_configs)

    @b.errormsg("Failure while cluster scaling: ")
    def _check_scaling(self):
        change_list = [
            {
                'operation': 'resize',
                'info': ['worker-node-nm-dn', 1]
            },
            {
                'operation': 'resize',
                'info': ['worker-node-dn', 0]
            },
            {
                'operation': 'resize',
                'info': ['worker-node-nm', 0]
            },
            {
                'operation': 'add',
                'info': [
                    'new-worker-node-nm', 1, '%s' % self.ng_tmpl_nm_id
                ]
            },
            {
                'operation': 'add',
                'info': [
                    'new-worker-node-dn', 1, '%s' % self.ng_tmpl_dn_id
                ]
            }
        ]

        self.cluster_info = self.cluster_scaling(self.cluster_info,
                                                 change_list)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.vanilla_two_config)

    @b.errormsg("Failure while Cinder testing after cluster scaling: ")
    def _check_cinder_after_scaling(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing after cluster scaling: ")
    def _check_mapreduce_after_scaling(self):
        self.map_reduce_testing(self.cluster_info)

    @b.errormsg(
        "Failure during check of Swift availability after cluster scaling: ")
    def _check_swift_after_scaling(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing after cluster scaling: ")
    def _check_edp_after_scaling(self):
        self._check_edp()

    @testcase.skipIf(
        cfg.ITConfig().vanilla_two_config.SKIP_ALL_TESTS_FOR_PLUGIN,
        "All tests for Vanilla plugin were skipped")
    @testcase.attr('vanilla2')
    def test_vanilla_two_plugin_gating(self):
        self._prepare_test()
        self._create_nm_dn_ng_template()
        self._create_nm_ng_template()
        self._create_dn_ng_template()
        self._create_cluster_template()
        self._create_cluster()

        self._check_cinder()
        self._check_mapreduce()
        self._check_swift()
        self._check_edp()

        if not self.vanilla_two_config.SKIP_SCALING_TEST:
            self._check_scaling()
            self._check_cinder_after_scaling()
            self._check_mapreduce_after_scaling()
            self._check_swift_after_scaling()
            self._check_edp_after_scaling()

    def tearDown(self):
        self.delete_objects(self.cluster_id, self.cluster_template_id,
                            self.ng_template_ids)
        super(VanillaTwoGatingTest, self).tearDown()
