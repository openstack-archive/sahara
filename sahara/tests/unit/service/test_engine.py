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

import mock

from sahara.service import engine
from sahara.tests.unit import base


class TestEngine(base.SaharaWithDbTestCase):

    class EngineTest(engine.Engine):

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

    def setUp(self):
        super(TestEngine, self).setUp()
        self.eng = self.EngineTest()

    @mock.patch('sahara.utils.openstack.nova.client')
    def test_get_node_group_image_username(self, nova_client):
        ng = mock.Mock()
        client = mock.Mock()
        client.images.get.return_value = mock.Mock(username='username')
        nova_client.return_value = client

        self.assertEqual(
            'username', self.eng.get_node_group_image_username(ng))

    @mock.patch('sahara.utils.cluster_progress_ops.add_successful_event')
    @mock.patch('sahara.service.networks.init_instances_ips',
                return_value=True)
    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.general.check_cluster_exists', return_value=True)
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
