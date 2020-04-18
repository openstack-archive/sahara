# Copyright (c) 2015 Mirantis Inc.
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
from sahara.plugins import provisioning as pr_base
from sahara.service import api as service_api
from sahara.service.api import v10 as api
from sahara.tests.unit import base
from sahara.utils import cluster as c_u

conductor = cond.API

SAMPLE_CLUSTER = {
    'plugin_name': 'fake',
    'hadoop_version': 'test_version',
    'tenant_id': 'tenant_1',
    'name': 'test_cluster',
    'user_keypair_id': 'my_keypair',
    'node_groups': [
        {
            'auto_security_group': True,
            'name': 'ng_1',
            'flavor_id': '42',
            'node_processes': ['p1', 'p2'],
            'count': 1
        },
        {
            'auto_security_group': False,
            'name': 'ng_2',
            'flavor_id': '42',
            'node_processes': ['p3', 'p4'],
            'count': 3
        },
        {
            'auto_security_group': False,
            'name': 'ng_3',
            'flavor_id': '42',
            'node_processes': ['p3', 'p4'],
            'count': 1
        }
    ],
    'cluster_configs': {
        'service_1': {
            'config_2': 'value_2'
        },
        'service_2': {
            'config_1': 'value_1'
        }
    },
}

SCALE_DATA = {
    'resize_node_groups': [
        {
            'name': 'ng_1',
            'count': 3,
        },
        {
            'name': 'ng_2',
            'count': 2,
        }
    ],
    'add_node_groups': [
        {
            'auto_security_group': True,
            'name': 'ng_4',
            'flavor_id': '42',
            'node_processes': ['p1', 'p2'],
            'count': 1
        },
    ]
}


class FakePlugin(pr_base.ProvisioningPluginBase):
    _info = {}
    name = "fake"

    def __init__(self, calls_order):
        self.calls_order = calls_order

    def configure_cluster(self, cluster):
        pass

    def start_cluster(self, cluster):
        pass

    def get_description(self):
        return "Some description"

    def get_title(self):
        return "Fake plugin"

    def validate(self, cluster):
        self.calls_order.append('validate')

    def get_open_ports(self, node_group):
        self.calls_order.append('get_open_ports')

    def validate_scaling(self, cluster, to_be_enlarged, additional):
        self.calls_order.append('validate_scaling')

    def get_versions(self):
        return ['0.1', '0.2']

    def get_node_processes(self, version):
        return {'HDFS': ['namenode', 'datanode']}

    def get_configs(self, version):
        return []

    def recommend_configs(self, cluster, scaling=False):
        self.calls_order.append('recommend_configs')


class FakePluginManager(pl_base.PluginManager):
    def __init__(self, calls_order):
        super(FakePluginManager, self).__init__()
        self.plugins['fake'] = FakePlugin(calls_order)


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


class TestApi(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestApi, self).setUp()
        self.calls_order = []
        self.override_config('plugins', ['fake'])
        pl_base.PLUGINS = FakePluginManager(self.calls_order)
        service_api.setup_api(FakeOps(self.calls_order))
        oslo_messaging.notify.notifier.Notifier.info = mock.Mock()
        self.ctx = context.ctx()

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    def test_create_cluster_success(self, check_cluster):
        cluster = api.create_cluster(SAMPLE_CLUSTER)
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
        MULTIPLE_CLUSTERS = SAMPLE_CLUSTER.copy()
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
        MULTIPLE_CLUSTERS = SAMPLE_CLUSTER.copy()
        MULTIPLE_CLUSTERS['count'] = 2
        check_cluster.side_effect = exc.QuotaException(
            'resource', 'requested', 'available')
        with testtools.ExpectedException(exc.QuotaException):
            api.create_cluster(SAMPLE_CLUSTER)
        self.assertEqual('Error', api.get_clusters()[0].status)

    @mock.patch('sahara.service.quotas.check_cluster')
    def test_create_cluster_failed(self, check_cluster):
        check_cluster.side_effect = exc.QuotaException(
            'resource', 'requested', 'available')
        with testtools.ExpectedException(exc.QuotaException):
            api.create_cluster(SAMPLE_CLUSTER)
        self.assertEqual('Error', api.get_clusters()[0].status)

    @mock.patch('sahara.service.quotas.check_cluster', return_value=None)
    @mock.patch('sahara.service.quotas.check_scaling', return_value=None)
    def test_scale_cluster_success(self, check_scaling, check_cluster):
        cluster = api.create_cluster(SAMPLE_CLUSTER)
        api.scale_cluster(cluster.id, SCALE_DATA)
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
        cluster = api.create_cluster(SAMPLE_CLUSTER)
        check_scaling.side_effect = exc.QuotaException(
            'resource', 'requested', 'available')
        with testtools.ExpectedException(exc.QuotaException):
            api.scale_cluster(cluster.id, {})

    def test_cluster_update(self):
        with mock.patch('sahara.service.quotas.check_cluster'):
            cluster = api.create_cluster(SAMPLE_CLUSTER)
            updated_cluster = api.update_cluster(
                cluster.id, {'description': 'Cluster'})
            self.assertEqual('Cluster', updated_cluster.description)

    def test_get_plugin(self):
        # processing to dict
        data = api.get_plugin('fake', '0.1').dict
        self.assertIsNotNone(data)
        self.assertEqual(
            len(pr_base.list_of_common_configs()), len(data.get('configs')))
        self.assertEqual(['fake', '0.1'], data.get('required_image_tags'))
        self.assertEqual(
            {'HDFS': ['namenode', 'datanode']}, data.get('node_processes'))

        self.assertIsNone(api.get_plugin('fake', '0.3'))
        data = api.get_plugin('fake').dict
        self.assertIsNotNone(data.get('version_labels'))
        self.assertIsNotNone(data.get('plugin_labels'))
        del data['plugin_labels']
        del data['version_labels']

        self.assertEqual({
            'description': "Some description",
            'name': 'fake',
            'title': 'Fake plugin',
            'versions': ['0.1', '0.2']}, data)
        self.assertIsNone(api.get_plugin('name1', '0.1'))

    def test_update_plugin(self):
        data = api.get_plugin('fake', '0.1').dict
        self.assertIsNotNone(data)

        updated = api.update_plugin('fake', values={
            'plugin_labels': {'enabled': {'status': False}}}).dict
        self.assertFalse(updated['plugin_labels']['enabled']['status'])

        updated = api.update_plugin('fake', values={
            'plugin_labels': {'enabled': {'status': True}}}).dict
        self.assertTrue(updated['plugin_labels']['enabled']['status'])

        # restore to original status
        updated = api.update_plugin('fake', values={
            'plugin_labels': data['plugin_labels']}).dict
        self.assertEqual(data['plugin_labels']['enabled']['status'],
                         updated['plugin_labels']['enabled']['status'])
