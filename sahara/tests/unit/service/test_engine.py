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


from heatclient import exc as heat_exc
from unittest import mock

from sahara.service import engine
from sahara.service.heat import heat_engine
from sahara.tests.unit import base


class EngineTest(engine.Engine):
    def __init__(self):
        super(EngineTest, self).__init__()
        self.order = []

    def create_cluster(self, cluster):
        pass

    def get_type_and_version(self):
        pass

    def rollback_cluster(self, cluster, reason):
        pass

    def scale_cluster(self, cluster, node_group_id_map):
        pass

    def shutdown_cluster(self, cluster):
        pass


class TestEngine(base.SaharaWithDbTestCase):

    def setUp(self):
        super(TestEngine, self).setUp()
        self.eng = EngineTest()

    @mock.patch('sahara.utils.openstack.images.SaharaImageManager')
    def test_get_node_group_image_username(self, mock_manager):
        ng = mock.Mock()
        manager = mock.Mock()
        manager.get.return_value = mock.Mock(username='username')
        mock_manager.return_value = manager

        self.assertEqual(
            'username', self.eng.get_node_group_image_username(ng))

    @mock.patch('sahara.utils.cluster_progress_ops.add_successful_event')
    @mock.patch('sahara.service.networks.init_instances_ips',
                return_value=True)
    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.cluster.check_cluster_exists', return_value=True)
    def test_ips_assign(self, g, ctx, init, ops):
        cluster = mock.Mock()
        instances = [mock.Mock(id='1'), mock.Mock(id='2')]
        instances_with_ip = set()
        self.eng._ips_assign(instances_with_ip, cluster, instances)
        self.assertEqual({'1', '2'}, instances_with_ip)

    @mock.patch('datetime.datetime')
    @mock.patch('sahara.context.ctx')
    @mock.patch('sahara.service.engine.conductor')
    def test_clean_job_executions(self, conductor, ctx, date):
        cluster = mock.Mock()
        je = mock.Mock(info=None, end_time=None)
        conductor.job_execution_get_all.return_value = [je]
        date.now.return_value = '28.04.2015'

        self.eng._clean_job_executions(cluster)

        args, kwargs = conductor.job_execution_update.call_args
        update = {
            'info': {'status': 'KILLED'},
            'cluster_id': None,
            'end_time': '28.04.2015'}

        self.assertEqual(update, args[2])


class TestDeletion(base.SaharaTestCase):
    def setUp(self):
        super(TestDeletion, self).setUp()
        self.engine = EngineTest()

    @mock.patch('sahara.service.engine.Engine._remove_db_objects')
    @mock.patch('sahara.service.engine.Engine._clean_job_executions')
    @mock.patch('sahara.utils.openstack.heat.client')
    @mock.patch('sahara.service.heat.heat_engine.LOG.warning')
    def test_calls_order(self, logger, heat_client, _job_ex, _db_ob):
        class FakeHeatEngine(heat_engine.HeatEngine):
            def __init__(self):
                super(FakeHeatEngine, self).__init__()
                self.order = []

            def _clean_job_executions(self, cluster):
                self.order.append('clean_job_executions')
                super(FakeHeatEngine, self)._clean_job_executions(cluster)

            def _remove_db_objects(self, cluster):
                self.order.append('remove_db_objects')
                super(FakeHeatEngine, self)._remove_db_objects(cluster)

        fake_cluster = mock.Mock()
        heat_client.side_effect = heat_exc.HTTPNotFound()
        engine = FakeHeatEngine()
        engine.shutdown_cluster(fake_cluster)
        self.assertEqual(['clean_job_executions', 'remove_db_objects'],
                         engine.order)
        self.assertEqual(
            [mock.call('Did not find stack for cluster.')],
            logger.call_args_list
        )

    @mock.patch('sahara.service.heat.heat_engine.LOG.error')
    @mock.patch('sahara.utils.openstack.heat.delete_stack')
    @mock.patch('sahara.utils.openstack.heat.lazy_delete_stack')
    @mock.patch('sahara.service.engine.Engine._remove_db_objects')
    @mock.patch('sahara.service.engine.Engine._clean_job_executions')
    def test_force_delete_calls(self, cj, rdb, lazy_delete, delete, log_err):
        engine = heat_engine.HeatEngine()

        # Force delete (lazy_delete)
        engine.shutdown_cluster(mock.Mock(), force=True)
        self.assertEqual(delete.call_count, 0)
        self.assertEqual(lazy_delete.call_count, 1)
        self.assertEqual(cj.call_count, 1)
        self.assertEqual(rdb.call_count, 1)

        delete.reset_mock()
        lazy_delete.reset_mock()
        rdb.reset_mock()
        cj.reset_mock()

        # Regular delete
        engine.shutdown_cluster(mock.Mock(), force=False)
        self.assertEqual(delete.call_count, 1)
        self.assertEqual(lazy_delete.call_count, 0)
        self.assertEqual(cj.call_count, 1)
        self.assertEqual(rdb.call_count, 1)
