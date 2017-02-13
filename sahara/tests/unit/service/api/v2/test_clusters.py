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

import mock
import oslo_messaging
import six
import testtools

from sahara import conductor as cond
from sahara import context
from sahara import exceptions as exc
from sahara.plugins import base as pl_base
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
        conductor.cluster_update(
            context.ctx(), id, {'status': c_u.CLUSTER_STATUS_ACTIVE})

    def provision_scaled_cluster(self, id, to_be_enlarged):
        self.calls_order.append('ops.provision_scaled_cluster')
        # Set scaled to see difference between active and scaled
        for (ng, count) in six.iteritems(to_be_enlarged):
            conductor.node_group_update(context.ctx(), ng, {'count': count})
        conductor.cluster_update(context.ctx(), id, {'status': 'Scaled'})

    def terminate_cluster(self, id):
        self.calls_order.append('ops.terminate_cluster')


class TestClusterApi(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestClusterApi, self).setUp()
        self.calls_order = []
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
        result_cluster1 = api.get_cluster(clusters['clusters'][0])
        result_cluster2 = api.get_cluster(clusters['clusters'][1])
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
