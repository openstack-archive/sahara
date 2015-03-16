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


class CDHGatingTest(cluster_configs.ClusterConfigTest,
                    map_reduce.MapReduceTest, swift.SwiftTest,
                    scaling.ScalingTest, cinder.CinderVolumeTest, edp.EDPTest):

    cdh_config = cfg.ITConfig().cdh_config
    SKIP_MAP_REDUCE_TEST = cdh_config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = cdh_config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = cdh_config.SKIP_SCALING_TEST
    SKIP_CINDER_TEST = cdh_config.SKIP_CINDER_TEST
    SKIP_EDP_TEST = cdh_config.SKIP_EDP_TEST

    def setUp(self):
        super(CDHGatingTest, self).setUp()
        self.cluster_id = None
        self.cluster_template_id = None
        self.ng_template_ids = []

    def _prepare_test(self):
        self.cdh_config = cfg.ITConfig().cdh_config
        self.floating_ip_pool = self.common_config.FLOATING_IP_POOL
        self.internal_neutron_net = None
        if self.common_config.NEUTRON_ENABLED:
            self.internal_neutron_net = self.get_internal_neutron_net_id()
            self.floating_ip_pool = (
                self.get_floating_ip_pool_id_for_neutron_net())

        self.cdh_config.IMAGE_ID, self.cdh_config.SSH_USERNAME = (
            self.get_image_id_and_ssh_username(self.cdh_config))

        self.volumes_per_node = 0
        self.volume_size = 0
        if not self.SKIP_CINDER_TEST:
            self.volumes_per_node = 2
            self.volume_size = 2

    @b.errormsg("Failure while 'nm-dn' node group template creation: ")
    def _create_nm_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-cdh-nm-dn',
            'plugin_config': self.cdh_config,
            'description': 'test node group template for CDH plugin',
            'node_processes': ['NODEMANAGER', 'DATANODE'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_nm_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_nm_dn_id)

    @b.errormsg("Failure while 'nm' node group template creation: ")
    def _create_nm_ng_template(self):
        template = {
            'name': 'test-node-group-template-cdh-nm',
            'plugin_config': self.cdh_config,
            'description': 'test node group template for CDH plugin',
            'volumes_per_node': self.volumes_per_node,
            'volume_size': self.volume_size,
            'node_processes': ['NODEMANAGER'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_nm_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_nm_id)

    @b.errormsg("Failure while 'dn' node group template creation: ")
    def _create_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-cdh-dn',
            'plugin_config': self.cdh_config,
            'description': 'test node group template for CDH plugin',
            'volumes_per_node': self.volumes_per_node,
            'volume_size': self.volume_size,
            'node_processes': ['DATANODE'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_dn_id)

    @b.errormsg("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        cl_config = {
            'general': {
                'CDH5 repo list URL': self.cdh_config.CDH_REPO_LIST_URL,
                'CM5 repo list URL': self.cdh_config.CM_REPO_LIST_URL,
                'CDH5 repo key URL (for debian-based only)':
                self.cdh_config.CDH_APT_KEY_URL,
                'CM5 repo key URL (for debian-based only)':
                self.cdh_config.CM_APT_KEY_URL,
                'Enable Swift': True
            }
        }
        template = {
            'name': 'test-cluster-template-cdh',
            'plugin_config': self.cdh_config,
            'description': 'test cluster template for CDH plugin',
            'cluster_configs': cl_config,
            'node_groups': [
                {
                    'name': 'manager-node',
                    'flavor_id': self.cdh_config.MANAGERNODE_FLAVOR,
                    'node_processes': ['MANAGER'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
                },
                {
                    'name': 'master-node-rm-nn',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['NAMENODE', 'RESOURCEMANAGER'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
                },
                {
                    'name': 'master-node-oo-hs-snn',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['OOZIE_SERVER', 'JOBHISTORY',
                                       'SECONDARYNAMENODE'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
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
        cluster_name = '%s-%s' % (self.common_config.CLUSTER_NAME,
                                  self.cdh_config.PLUGIN_NAME)
        cluster = {
            'name': cluster_name,
            'plugin_config': self.cdh_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {
                'HDFS': {
                    'dfs_replication': 1
                }
            }
        }
        self.create_cluster(**cluster)
        self.cluster_info = self.get_cluster_info(self.cdh_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.cdh_config)

    @b.errormsg("Failure while Cinder testing: ")
    def _check_cinder(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing: ")
    def _check_mapreduce(self):
        self.map_reduce_testing(self.cluster_info, check_log=False)

    @b.errormsg("Failure during check of Swift availability: ")
    def _check_swift(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing: ")
    def _check_edp(self):
        self._edp_test()

    def _edp_test(self):
        # check pig
        pig_job = self.edp_info.read_pig_example_script()
        pig_lib = self.edp_info.read_pig_example_jar()
        self.edp_testing(job_type=utils_edp.JOB_TYPE_PIG,
                         job_data_list=[{'pig': pig_job}],
                         lib_data_list=[{'jar': pig_lib}],
                         swift_binaries=False,
                         hdfs_local_output=True)

        # check mapreduce
        mapreduce_jar = self.edp_info.read_mapreduce_example_jar()
        mapreduce_configs = self.edp_info.mapreduce_example_configs()
        self.edp_testing(job_type=utils_edp.JOB_TYPE_MAPREDUCE,
                         job_data_list=[],
                         lib_data_list=[{'jar': mapreduce_jar}],
                         configs=mapreduce_configs,
                         swift_binaries=False,
                         hdfs_local_output=True)

        # check mapreduce streaming
        self.edp_testing(job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
                         job_data_list=[],
                         lib_data_list=[],
                         configs=self.edp_info.mapreduce_streaming_configs(),
                         swift_binaries=False,
                         hdfs_local_output=True)

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
                                               self.cdh_config)

    @b.errormsg("Failure while Cinder testing after cluster scaling: ")
    def _check_cinder_after_scaling(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing after cluster scaling: ")
    def _check_mapreduce_after_scaling(self):
        self.map_reduce_testing(self.cluster_info, check_log=False)

    @b.errormsg(
        "Failure during check of Swift availability after cluster scaling: ")
    def _check_swift_after_scaling(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing after cluster scaling: ")
    def _check_edp_after_scaling(self):
        self._edp_test()

    @testcase.skipIf(
        cfg.ITConfig().cdh_config.SKIP_ALL_TESTS_FOR_PLUGIN,
        "All tests for CDH plugin were skipped")
    @testcase.attr('cdh')
    def test_cdh_plugin_gating(self):
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

        if not self.cdh_config.SKIP_SCALING_TEST:
            self._check_scaling()
            self._check_cinder_after_scaling()
            self._check_edp_after_scaling()

    def tearDown(self):
        self.delete_objects(self.cluster_id, self.cluster_template_id,
                            self.ng_template_ids)
        super(CDHGatingTest, self).tearDown()
