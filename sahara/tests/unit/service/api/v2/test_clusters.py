# Copyright (c) 2017 EasyStack Inc.
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

from unittest import mock

import oslo_messaging
import six
import testtools

from sahara import conductor as cond
from sahara import context
from sahara import exceptions as exc
from sahara.plugins import base as pl_base
from sahara.plugins import utils as u
from sahara.service import api as service_api
from sahara.service.api.v2 import clusters as api
from sahara.tests.unit import base
import sahara.tests.unit.service.api.v2.base as api_base
from sahara.utils import cluster as c_u

conductor = cond.API


class FakeOps(object):
    def __init__(self, calls_order):
        self.calls_order = calls_order

    def provision_cluster(self, id):
        self.calls_order.append('ops.provision_cluster')
        cluster = conductor.cluster_get(context.ctx(), id)
        target_count = {}
        for node_group in cluster.node_groups:
            target_count[node_group.id] = node_group.count

        for node_group in cluster.node_groups:
            conductor.node_group_update(context.ctx(),
                                        node_group, {"count": 0})

        for node_group in cluster.node_groups:
            for i in range(target_count[node_group.id]):
                inst = {
                    "instance_id": node_group.name + '_' + str(i),
                    "instance_name": node_group.name + '_' + str(i)
                }
                conductor.instance_add(context.ctx(), node_group, inst)
        conductor.cluster_update(
            context.ctx(), id, {'status': c_u.CLUSTER_STATUS_ACTIVE})

    def provision_scaled_cluster(self, id, to_be_enlarged,
                                 node_group_instance_map=None):
        self.calls_order.append('ops.provision_scaled_cluster')
        cluster = conductor.cluster_get(context.ctx(), id)

        # Set scaled to see difference between active and scaled
        for (ng, count) in six.iteritems(to_be_enlarged):
            instances_to_delete = []
            if node_group_instance_map:
                if ng in node_group_instance_map:
                    instances_to_delete = self._get_instance(
                        cluster, node_group_instance_map[ng])
            for instance in instances_to_delete:
                conductor.instance_remove(context.ctx(), instance)

            conductor.node_group_update(context.ctx(), ng, {'count': count})
        conductor.cluster_update(context.ctx(), id, {'status': 'Scaled'})

    def update_keypair(self, id):
        self.calls_order.append('ops.update_keypair')
        cluster = conductor.cluster_get(context.ctx(), id)
        keypair_name = cluster.user_keypair_id
        nova_p = mock.patch("sahara.utils.openstack.nova.client")
        nova = nova_p.start()
        key = nova.get_keypair(keypair_name)
        nodes = u.get_instances(cluster)
        for instance in nodes:
            remote = mock.Mock()
            remote.execute_command(
                "echo {keypair} >> ~/.ssh/authorized_keys".format(
                    keypair=key.public_key))
            remote.reset_mock()

    def terminate_cluster(self, id, force):
        self.calls_order.append('ops.terminate_cluster')

    def _get_instance(self, cluster, instances_to_delete):
        instances = []
        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                if instance.instance_id in instances_to_delete:
                    instances.append(instance)
        return instances


class TestClusterApi(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestClusterApi, self).setUp()
        self.calls_order = []
        self.override_config('plugins', ['fake'])
        pl_base.PLUGINS = api_base.FakePluginManager(self.calls_order)
        service_api.setup_api(FakeOps(self.calls_order))
        oslo_messaging.notify.notifier.Notifier.info = mock.Mock()
        self.ctx = context.ctx()

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    def test_create_cluster_success(self, check_cluster):
        cluster = api.create_cluster(api_base.SAMPLE_CLUSTER)
        self.assertEqual(1, check_cluster.call_count)
        result_cluster = api.get_cluster(cluster.id)
        self.assertEqual(c_u.CLUSTER_STATUS_ACTIVE, result_cluster.status)
        expected_count = {
            'ng_1': 1,
            'ng_2': 3,
            'ng_3': 1,
        }
        ng_count = 0
        for ng in result_cluster.node_groups:
            self.assertEqual(expected_count[ng.name], ng.count)
            ng_count += 1
        self.assertEqual(3, ng_count)
        api.terminate_cluster(result_cluster.id)
        self.assertEqual(
            ['get_open_ports', 'recommend_configs', 'validate',
             'ops.provision_cluster',
             'ops.terminate_cluster'], self.calls_order)

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    def test_create_multiple_clusters_success(self, check_cluster):
        MULTIPLE_CLUSTERS = api_base.SAMPLE_CLUSTER.copy()
        MULTIPLE_CLUSTERS['count'] = 2
        clusters = api.create_multiple_clusters(MULTIPLE_CLUSTERS)
        self.assertEqual(2, check_cluster.call_count)
        result_cluster1 = api.get_cluster(
            clusters['clusters'][0]['cluster']['id'])
        result_cluster2 = api.get_cluster(
            clusters['clusters'][1]['cluster']['id'])
        self.assertEqual(c_u.CLUSTER_STATUS_ACTIVE, result_cluster1.status)
        self.assertEqual(c_u.CLUSTER_STATUS_ACTIVE, result_cluster2.status)
        expected_count = {
            'ng_1': 1,
            'ng_2': 3,
            'ng_3': 1,
        }
        ng_count = 0
        for ng in result_cluster1.node_groups:
            self.assertEqual(expected_count[ng.name], ng.count)
            ng_count += 1
        self.assertEqual(3, ng_count)
        api.terminate_cluster(result_cluster1.id)
        api.terminate_cluster(result_cluster2.id)
        self.assertEqual(
            ['get_open_ports', 'recommend_configs', 'validate',
             'ops.provision_cluster',
             'get_open_ports', 'recommend_configs', 'validate',
             'ops.provision_cluster',
             'ops.terminate_cluster',
             'ops.terminate_cluster'], self.calls_order)

    @mock.patch('sahara.service.quotas.check_cluster')
    def test_create_multiple_clusters_failed(self, check_cluster):
        MULTIPLE_CLUSTERS = api_base.SAMPLE_CLUSTER.copy()
        MULTIPLE_CLUSTERS['count'] = 2
        check_cluster.side_effect = exc.QuotaException(
            'resource', 'requested', 'available')
        with testtools.ExpectedException(exc.QuotaException):
            api.create_cluster(api_base.SAMPLE_CLUSTER)
        self.assertEqual('Error', api.get_clusters()[0].status)

    @mock.patch('sahara.service.quotas.check_cluster')
    def test_create_cluster_failed(self, check_cluster):
        check_cluster.side_effect = exc.QuotaException(
            'resource', 'requested', 'available')
        with testtools.ExpectedException(exc.QuotaException):
            api.create_cluster(api_base.SAMPLE_CLUSTER)
        self.assertEqual('Error', api.get_clusters()[0].status)

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    @mock.patch('sahara.service.quotas.check_scaling', return_value=None)
    def test_scale_cluster_success(self, check_scaling, check_cluster):
        cluster = api.create_cluster(api_base.SAMPLE_CLUSTER)
        cluster = api.get_cluster(cluster.id)
        api.scale_cluster(cluster.id, api_base.SCALE_DATA)
        result_cluster = api.get_cluster(cluster.id)
        self.assertEqual('Scaled', result_cluster.status)
        expected_count = {
            'ng_1': 3,
            'ng_2': 2,
            'ng_3': 1,
            'ng_4': 1,
        }
        ng_count = 0
        for ng in result_cluster.node_groups:
            self.assertEqual(expected_count[ng.name], ng.count)
            ng_count += 1
        self.assertEqual(4, ng_count)
        api.terminate_cluster(result_cluster.id)
        self.assertEqual(
            ['get_open_ports', 'recommend_configs', 'validate',
             'ops.provision_cluster', 'get_open_ports', 'get_open_ports',
             'recommend_configs', 'validate_scaling',
             'ops.provision_scaled_cluster',
             'ops.terminate_cluster'], self.calls_order)

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    @mock.patch('sahara.service.quotas.check_scaling', return_value=None)
    def test_scale_cluster_n_specific_instances_success(self, check_scaling,
                                                        check_cluster):
        cluster = api.create_cluster(api_base.SAMPLE_CLUSTER)
        cluster = api.get_cluster(cluster.id)
        api.scale_cluster(cluster.id, api_base.SCALE_DATA_N_SPECIFIC_INSTANCE)
        result_cluster = api.get_cluster(cluster.id)
        self.assertEqual('Scaled', result_cluster.status)
        expected_count = {
            'ng_1': 3,
            'ng_2': 1,
            'ng_3': 1,
        }
        ng_count = 0
        for ng in result_cluster.node_groups:
            self.assertEqual(expected_count[ng.name], ng.count)
            ng_count += 1
        self.assertEqual(1, result_cluster.node_groups[1].count)
        self.assertNotIn('ng_2_0',
                         self._get_instances_ids(
                             result_cluster.node_groups[1]))
        self.assertNotIn('ng_2_2',
                         self._get_instances_ids(
                             result_cluster.node_groups[1]))
        self.assertEqual(3, ng_count)
        api.terminate_cluster(result_cluster.id)
        self.assertEqual(
            ['get_open_ports', 'recommend_configs', 'validate',
             'ops.provision_cluster', 'get_open_ports',
             'recommend_configs', 'validate_scaling',
             'ops.provision_scaled_cluster',
             'ops.terminate_cluster'], self.calls_order)

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    @mock.patch('sahara.service.quotas.check_scaling', return_value=None)
    def test_scale_cluster_specific_and_non_specific(self, check_scaling,
                                                     check_cluster):
        cluster = api.create_cluster(api_base.SAMPLE_CLUSTER)
        cluster = api.get_cluster(cluster.id)
        api.scale_cluster(cluster.id, api_base.SCALE_DATA_SPECIFIC_INSTANCE)
        result_cluster = api.get_cluster(cluster.id)
        self.assertEqual('Scaled', result_cluster.status)
        expected_count = {
            'ng_1': 3,
            'ng_2': 1,
            'ng_3': 1,
        }
        ng_count = 0
        for ng in result_cluster.node_groups:
            self.assertEqual(expected_count[ng.name], ng.count)
            ng_count += 1
        self.assertEqual(1, result_cluster.node_groups[1].count)
        self.assertNotIn('ng_2_0',
                         self._get_instances_ids(
                             result_cluster.node_groups[1]))
        self.assertEqual(3, ng_count)
        api.terminate_cluster(result_cluster.id)
        self.assertEqual(
            ['get_open_ports', 'recommend_configs', 'validate',
             'ops.provision_cluster', 'get_open_ports',
             'recommend_configs', 'validate_scaling',
             'ops.provision_scaled_cluster',
             'ops.terminate_cluster'], self.calls_order)

    def _get_instances_ids(self, node_group):
        instance_ids = []
        for instance in node_group.instances:
            instance_ids.append(instance.instance_id)
        return instance_ids

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    @mock.patch('sahara.service.quotas.check_scaling', return_value=None)
    def test_scale_cluster_failed(self, check_scaling, check_cluster):
        cluster = api.create_cluster(api_base.SAMPLE_CLUSTER)
        check_scaling.side_effect = exc.QuotaException(
            'resource', 'requested', 'available')
        with testtools.ExpectedException(exc.QuotaException):
            api.scale_cluster(cluster.id, {})

    def test_cluster_update(self):
        with mock.patch('sahara.service.quotas.check_cluster'):
            cluster = api.create_cluster(api_base.SAMPLE_CLUSTER)
            updated_cluster = api.update_cluster(
                cluster.id, {'description': 'Cluster'})
            self.assertEqual('Cluster', updated_cluster.description)

    def test_cluster_keypair_update(self):
        with mock.patch('sahara.service.quotas.check_cluster'):
            cluster = api.create_cluster(api_base.SAMPLE_CLUSTER)
            api.update_cluster(cluster.id, {'update_keypair': True})
