# Copyright 2014 OpenStack Foundation.
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


class SparkGatingTest(swift.SwiftTest, scaling.ScalingTest,
                      edp.EDPTest):

    config = cfg.ITConfig().spark_config
    SKIP_EDP_TEST = config.SKIP_EDP_TEST

    def setUp(self):
        super(SparkGatingTest, self).setUp()
        self.cluster_id = None
        self.cluster_template_id = None
        self.ng_template_ids = []

    def _prepare_test(self):
        self.spark_config = cfg.ITConfig().spark_config
        self.floating_ip_pool = self.common_config.FLOATING_IP_POOL
        self.internal_neutron_net = None
        if self.common_config.NEUTRON_ENABLED:
            self.internal_neutron_net = self.get_internal_neutron_net_id()
            self.floating_ip_pool = (
                self.get_floating_ip_pool_id_for_neutron_net())

        self.spark_config.IMAGE_ID, self.spark_config.SSH_USERNAME = (
            self.get_image_id_and_ssh_username(self.spark_config))

    @b.errormsg("Failure while 'm-nn' node group template creation: ")
    def _create_m_nn_ng_template(self):
        template = {
            'name': 'test-node-group-template-spark-m-nn',
            'plugin_config': self.spark_config,
            'description': 'test node group template for Spark plugin',
            'node_processes': self.spark_config.MASTER_NODE_PROCESSES,
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_m_nn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_m_nn_id)

    @b.errormsg("Failure while 's-dn' node group template creation: ")
    def _create_s_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-spark-s-dn',
            'plugin_config': self.spark_config,
            'description': 'test node group template for Spark plugin',
            'node_processes': self.spark_config.WORKER_NODE_PROCESSES,
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_s_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_s_dn_id)

    @b.errormsg("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        template = {
            'name': 'test-cluster-template-spark',
            'plugin_config': self.spark_config,
            'description': 'test cluster template for Spark plugin',
            'cluster_configs': {
            },
            'node_groups': [
                {
                    'name': 'master-node',
                    'node_group_template_id': self.ng_tmpl_m_nn_id,
                    'count': 1
                },
                {
                    'name': 'worker-node',
                    'node_group_template_id': self.ng_tmpl_s_dn_id,
                    'count': 1
                }
            ],
            'net_id': self.internal_neutron_net
        }
        self.cluster_template_id = self.create_cluster_template(**template)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster_name = '%s-%s' % (self.common_config.CLUSTER_NAME,
                                  self.spark_config.PLUGIN_NAME)
        cluster = {
            'name': cluster_name,
            'plugin_config': self.spark_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {}
        }
        cluster_id = self.create_cluster(**cluster)
        self.poll_cluster_state(cluster_id)
        self.cluster_info = self.get_cluster_info(self.spark_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.spark_config)

    @b.errormsg("Failure while EDP testing: ")
    def _check_edp(self):
        self._edp_test()

    def _edp_test(self):
        # check spark
        spark_jar = self.edp_info.read_spark_example_jar()
        spark_configs = self.edp_info.spark_example_configs()
        job_id = self.edp_testing(
            utils_edp.JOB_TYPE_SPARK,
            job_data_list=[{'jar': spark_jar}],
            lib_data_list=[],
            configs=spark_configs)
        self.poll_jobs_status([job_id])

    @b.errormsg("Failure while cluster scaling: ")
    def _check_scaling(self):
        pass

    @b.errormsg("Failure while EDP testing after cluster scaling: ")
    def _check_edp_after_scaling(self):
        # Leave this blank until scaling is implemented
        pass

    @testcase.attr('spark')
    @testcase.skipIf(config.SKIP_ALL_TESTS_FOR_PLUGIN,
                     'All tests for Spark plugin were skipped')
    def test_spark_plugin_gating(self):

        self._prepare_test()
        self._create_m_nn_ng_template()
        self._create_s_dn_ng_template()
        self._create_cluster_template()
        self._create_cluster()

        self._check_edp()

        if not self.spark_config.SKIP_SCALING_TEST:
            self._check_scaling()
            self._check_edp_after_scaling()

    def tearDown(self):
        self.delete_objects(self.cluster_id, self.cluster_template_id,
                            self.ng_template_ids)
        super(SparkGatingTest, self).tearDown()
