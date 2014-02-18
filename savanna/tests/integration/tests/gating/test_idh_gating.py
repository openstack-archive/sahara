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
import unittest2

from savanna.openstack.common import excutils
from savanna.tests.integration.configs import config as cfg
from savanna.tests.integration.tests import base
from savanna.tests.integration.tests import cluster_configs
from savanna.tests.integration.tests import edp
from savanna.tests.integration.tests import map_reduce
from savanna.tests.integration.tests import scaling
from savanna.tests.integration.tests import swift


def errormessage(message):
    def decorator(fct):
        def wrapper(*args, **kwargs):
            try:
                fct(*args, **kwargs)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    base.ITestCase.print_error_log(message, e)

        return wrapper
    return decorator


class IDHGatingTest(cluster_configs.ClusterConfigTest, edp.EDPTest,
                    map_reduce.MapReduceTest, swift.SwiftTest,
                    scaling.ScalingTest):

    idh_config = cfg.ITConfig().idh_config
    SKIP_MAP_REDUCE_TEST = idh_config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = idh_config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = idh_config.SKIP_SCALING_TEST

    def setUp(self):
        super(IDHGatingTest, self).setUp()

        self.idh_config = cfg.ITConfig().idh_config
        self.floating_ip_pool = self.common_config.FLOATING_IP_POOL
        self.internal_neutron_net = None
        if self.common_config.NEUTRON_ENABLED:
            self.internal_neutron_net = self.get_internal_neutron_net_id()
            self.floating_ip_pool = \
                self.get_floating_ip_pool_id_for_neutron_net()

        self.cluster_id = None
        self.cluster_template_id = None
        self.ng_template_ids = []

    @errormessage("Failure while 'tt-dn' node group template creation: ")
    def _create_tt_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-idh-tt-dn',
            'plugin_config': self.idh_config,
            'description': 'test node group template for Intel plugin',
            'volumes_per_node': 0,
            'volume_size': 0,
            'node_processes': ['tasktracker', 'datanode'],
            'floating_ip_pool': self.floating_ip_pool,
            'node_configs': {}
        }
        self.ng_tmpl_tt_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_tt_dn_id)

    @errormessage("Failure while 'tt' node group template creation: ")
    def _create_tt_ng_template(self):
        template = {
            'name': 'test-node-group-template-idh-tt',
            'plugin_config': self.idh_config,
            'description': 'test node group template for Intel plugin',
            'volumes_per_node': 0,
            'volume_size': 0,
            'node_processes': ['tasktracker'],
            'floating_ip_pool': self.floating_ip_pool,
            'node_configs': {}
        }
        self.ng_tmpl_tt_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_tt_id)

    @errormessage("Failure while 'dn' node group template creation: ")
    def _create_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-idh-dn',
            'plugin_config': self.idh_config,
            'description': 'test node group template for Intel plugin',
            'volumes_per_node': 0,
            'volume_size': 0,
            'node_processes': ['datanode'],
            'floating_ip_pool': self.floating_ip_pool,
            'node_configs': {}
        }
        self.ng_tmpl_dn_id = self.create_node_group_template(**template)
        self.ng_template_ids.append(self.ng_tmpl_dn_id)

    @errormessage("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        template = {
            'name': 'test-cluster-template-idh',
            'plugin_config': self.idh_config,
            'description': 'test cluster template for Intel plugin',
            'cluster_configs': {
                'general': {
                    'Enable Swift': True,
                    'IDH tarball URL': self.idh_config.IDH_TARBALL_URL,
                    'IDH repository URL': self.idh_config.IDH_REPO_URL,
                    'OS repository URL': self.idh_config.OS_REPO_URL
                },
                'HDFS': {
                    'dfs.replication': 1
                }
            },
            'node_groups': [
                {
                    'name': 'manager-node',
                    'flavor_id': self.idh_config.MANAGER_FLAVOR_ID,
                    'node_processes': ['manager'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'count': 1
                },
                {
                    'name': 'master-node-jt-nn',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['namenode', 'jobtracker'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'count': 1
                },
                {
                    'name': 'worker-node-tt-dn',
                    'node_group_template_id': self.ng_tmpl_tt_dn_id,
                    'count': 2
                },
                {
                    'name': 'worker-node-dn',
                    'node_group_template_id': self.ng_tmpl_dn_id,
                    'count': 1
                },
                {
                    'name': 'worker-node-tt',
                    'node_group_template_id': self.ng_tmpl_tt_id,
                    'count': 1
                }
            ],
            'net_id': self.internal_neutron_net
        }
        self.cluster_template_id = self.create_cluster_template(**template)

    @errormessage("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster = {
            'plugin_config': self.idh_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {}
        }
        self.cluster_info = self.create_cluster_and_get_info(**cluster)

    @errormessage("Failure while Map Reduce testing: ")
    def _check_mapreduce(self):
        self.map_reduce_testing(self.cluster_info)

    @errormessage("Failure during check of Swift availability: ")
    def _check_swift(self):
        self.check_swift_availability(self.cluster_info)

    @errormessage("Failure while cluster scaling: ")
    def _check_scaling(self):
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
                    'new-worker-node-tt', 1, '%s' % self.ng_tmpl_tt_id
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

    @errormessage("Failure while Map Reduce testing after cluster scaling: ")
    def _check_mapreduce_after_scaling(self):
        if not self.idh_config.SKIP_SCALING_TEST:
                self.map_reduce_testing(self.cluster_info)

    @errormessage(
        "Failure during check of Swift availability after cluster scaling: ")
    def _check_swift_after_scaling(self):
        if not self.idh_config.SKIP_SCALING_TEST:
            self.check_swift_availability(self.cluster_info)

    @unittest2.skipIf(cfg.ITConfig().idh_config.SKIP_ALL_TESTS_FOR_PLUGIN,
                      "All tests for Intel plugin were skipped")
    @testcase.attr('idh')
    def test_idh_plugin_gating(self):
        self._create_tt_dn_ng_template()
        self._create_tt_ng_template()
        self._create_dn_ng_template()
        self._create_cluster_template()
        self._create_cluster()

        self._check_mapreduce()
        self._check_swift()
        self._check_scaling()
        self._check_mapreduce_after_scaling()
        self._check_swift_after_scaling()

    def tearDown(self):
        self.delete_objects(self.cluster_id, self.cluster_template_id,
                            self.ng_template_ids)
        super(IDHGatingTest, self).tearDown()
