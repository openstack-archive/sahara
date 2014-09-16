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

import mock

from sahara.plugins import base as base_plugins
from sahara.service import ops
from sahara.tests.unit import base


class FakeNodeGroup():
    id = 'id'
    count = 2
    instances = [1, 2]


class FakePlugin(mock.Mock):
    node_groups = [FakeNodeGroup()]

    def update_infra(self, cluster):
        TestOPS.SEQUENCE.append('update_infra')

    def configure_cluster(self, cluster):
        TestOPS.SEQUENCE.append('configure_cluster')

    def start_cluster(self, cluster):
        TestOPS.SEQUENCE.append('start_cluster')

    def on_terminate_cluster(self, cluster):
        TestOPS.SEQUENCE.append('on_terminate_cluster')

    def decommission_nodes(self, cluster, instances_to_delete):
        TestOPS.SEQUENCE.append('decommission_nodes')

    def scale_cluster(self, cluster, node_group_id_map):
        TestOPS.SEQUENCE.append('plugin.scale_cluster')

    def cluster_destroy(self, ctx, cluster):
        TestOPS.SEQUENCE.append('cluster_destroy')


class FakeINFRA():
    def create_cluster(self, cluster):
        TestOPS.SEQUENCE.append('create_cluster')

    def scale_cluster(self, cluster, node_group_id_map):
        TestOPS.SEQUENCE.append('INFRA.scale_cluster')
        return True

    def shutdown_cluster(self, cluster):
        TestOPS.SEQUENCE.append('shutdown_cluster')

    def rollback_cluster(self, cluster, reason):
        TestOPS.SEQUENCE.append('rollback_cluster')


class TestOPS(base.SaharaTestCase):
    SEQUENCE = []

    @mock.patch('sahara.service.ops._update_sahara_info')
    @mock.patch('sahara.service.ops._prepare_provisioning',
                return_value=(mock.Mock(), mock.Mock(), FakePlugin()))
    @mock.patch('sahara.utils.general.change_cluster_status')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.service.ops.CONF')
    @mock.patch('sahara.service.trusts.create_trust_for_cluster')
    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.service.edp.job_manager.run_job')
    def test_provision_cluster(self, p_run_job, p_job_exec, p_create_trust,
                               p_conf, p_cluster_get, p_change_status,
                               p_prep_provisioning, p_update_sahara_info):
        del self.SEQUENCE[:]
        ops.INFRA = FakeINFRA()
        ops._provision_cluster('123')
        # checking that order of calls is right
        self.assertEqual(['update_infra', 'create_cluster',
                          'configure_cluster', 'start_cluster'], self.SEQUENCE,
                         'Order of calls is wrong')

    @mock.patch('sahara.service.ops._prepare_provisioning',
                return_value=(mock.Mock(), mock.Mock(), FakePlugin()))
    @mock.patch('sahara.utils.general.change_cluster_status',
                return_value=FakePlugin())
    @mock.patch('sahara.utils.general.get_instances')
    def test_provision_scaled_cluster(self, p_get_instances, p_change_status,
                                      p_prep_provisioning):
        del self.SEQUENCE[:]
        ops.INFRA = FakeINFRA()
        ops._provision_scaled_cluster('123', {'id': 1})
        # checking that order of calls is right
        self.assertEqual(['decommission_nodes', 'INFRA.scale_cluster',
                          'plugin.scale_cluster'], self.SEQUENCE,
                         'Order of calls is wrong')

    @mock.patch('sahara.service.ops.CONF')
    @mock.patch('sahara.service.trusts.delete_trust_from_cluster')
    @mock.patch('sahara.context.ctx')
    def test_terminate_cluster(self, p_ctx, p_delete_trust, p_conf):
        del self.SEQUENCE[:]
        base_plugins.PLUGINS = FakePlugin()
        base_plugins.PLUGINS.get_plugin.return_value = FakePlugin()
        ops.INFRA = FakeINFRA()
        ops.conductor = FakePlugin()
        ops.terminate_cluster('123')
        # checking that order of calls is right
        self.assertEqual(['on_terminate_cluster', 'shutdown_cluster',
                         'cluster_destroy'], self.SEQUENCE,
                         'Order of calls is wrong')
