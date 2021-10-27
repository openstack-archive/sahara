# Copyright (c) 2013 Mirantis Inc.
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

import datetime
from unittest import mock

from oslo_utils import timeutils

from sahara.conductor import manager
from sahara import context
from sahara.service.castellan import config as castellan
import sahara.service.periodic as p
import sahara.tests.unit.base as base
from sahara.tests.unit.conductor.manager import test_clusters as tc
from sahara.tests.unit.conductor.manager import test_edp as te
from sahara.utils import cluster as c_u


class TestPeriodicBack(base.SaharaWithDbTestCase):

    def setUp(self):
        super(TestPeriodicBack, self).setUp()
        self.api = manager.ConductorManager()
        castellan.validate_config()

    @mock.patch('sahara.service.edp.job_manager.get_job_status')
    def test_job_status_update(self, get_job_status):
        ctx = context.ctx()
        job = self.api.job_create(ctx, te.SAMPLE_JOB)
        ds = self.api.data_source_create(ctx, te.SAMPLE_DATA_SOURCE)
        self._create_job_execution({"end_time": datetime.datetime.now(),
                                    "id": 1},
                                   job, ds, ds)
        self._create_job_execution({"end_time": None,
                                    "id": 2},
                                   job, ds, ds)
        self._create_job_execution({"end_time": None,
                                    "id": 3},
                                   job, ds, ds)
        p._make_periodic_tasks().update_job_statuses(None)
        self.assertEqual(2, get_job_status.call_count)
        get_job_status.assert_has_calls([mock.call('2'),
                                         mock.call('3')])

    @mock.patch('sahara.service.trusts.use_os_admin_auth_token')
    @mock.patch('sahara.service.api.v10.terminate_cluster')
    def test_transient_cluster_terminate(self, terminate_cluster,
                                         use_os_admin_auth_token):

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, 0, 0))

        ctx = context.ctx()
        job = self.api.job_create(ctx, te.SAMPLE_JOB)
        ds = self.api.data_source_create(ctx, te.SAMPLE_DATA_SOURCE)

        self._make_cluster('1')
        self._make_cluster('2')

        self._create_job_execution({"end_time": timeutils.utcnow(),
                                    "id": 1,
                                    "cluster_id": "1"},
                                   job, ds, ds)
        self._create_job_execution({"end_time": None,
                                    "id": 2,
                                    "cluster_id": "2"},
                                   job, ds, ds)
        self._create_job_execution({"end_time": None,
                                    "id": 3,
                                    "cluster_id": "2"},
                                   job, ds, ds)

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, 0, 1))

        p._make_periodic_tasks().terminate_unneeded_transient_clusters(None)
        self.assertEqual(1, terminate_cluster.call_count)
        terminate_cluster.assert_has_calls([mock.call('1')])
        self.assertEqual(1, use_os_admin_auth_token.call_count)

    @mock.patch('sahara.service.api.v10.terminate_cluster')
    def test_not_transient_cluster_does_not_terminate(self, terminate_cluster):

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, 0, 0))
        self._make_cluster('1', is_transient=False)
        timeutils.set_time_override(datetime.datetime(2005, 2, 1, 0, 1))
        p._make_periodic_tasks().terminate_unneeded_transient_clusters(None)

        self.assertEqual(0, terminate_cluster.call_count)

    @mock.patch('sahara.service.api.v10.terminate_cluster')
    def test_transient_cluster_not_killed_too_early(self, terminate_cluster):

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1')

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=20))

        p._make_periodic_tasks().terminate_unneeded_transient_clusters(None)
        self.assertEqual(0, terminate_cluster.call_count)

    @mock.patch('sahara.service.trusts.use_os_admin_auth_token')
    @mock.patch('sahara.service.api.v10.terminate_cluster')
    def test_transient_cluster_killed_in_time(self, terminate_cluster,
                                              use_os_admin_auth_token):

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1')

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=40))

        p._make_periodic_tasks().terminate_unneeded_transient_clusters(None)
        self.assertEqual(1, terminate_cluster.call_count)
        terminate_cluster.assert_has_calls([mock.call('1')])
        self.assertEqual(1, use_os_admin_auth_token.call_count)

    @mock.patch('sahara.service.api.v10.terminate_cluster')
    def test_incomplete_cluster_not_killed_too_early(self, terminate_cluster):

        self.override_config('cleanup_time_for_incomplete_clusters', 1)

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1', c_u.CLUSTER_STATUS_SPAWNING)

        timeutils.set_time_override(datetime.datetime(
            2005, 2, 1, minute=59, second=50))

        p._make_periodic_tasks().terminate_incomplete_clusters(None)
        self.assertEqual(0, terminate_cluster.call_count)

    @mock.patch('sahara.service.trusts.use_os_admin_auth_token')
    @mock.patch('sahara.service.api.v10.terminate_cluster')
    def test_incomplete_cluster_killed_in_time(self, terminate_cluster,
                                               use_os_admin_auth_token):

        self.override_config('cleanup_time_for_incomplete_clusters', 1)
        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1', c_u.CLUSTER_STATUS_SPAWNING)

        timeutils.set_time_override(datetime.datetime(
            2005, 2, 1, hour=1, second=10))

        p._make_periodic_tasks().terminate_incomplete_clusters(None)
        self.assertEqual(1, terminate_cluster.call_count)
        terminate_cluster.assert_has_calls([mock.call('1')])
        self.assertEqual(1, use_os_admin_auth_token.call_count)

    @mock.patch('sahara.service.api.v10.terminate_cluster')
    def test_active_cluster_not_killed_as_inactive(
            self, terminate_cluster):
        self.override_config('cleanup_time_for_incomplete_clusters', 1)

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1')

        timeutils.set_time_override(datetime.datetime(
            2005, 2, 1, hour=1, second=10))

        p._make_periodic_tasks().terminate_incomplete_clusters(None)
        self.assertEqual(0, terminate_cluster.call_count)

    @mock.patch("sahara.utils.proxy.proxy_domain_users_list")
    @mock.patch("sahara.utils.proxy.proxy_user_delete")
    @mock.patch("sahara.service.periodic.conductor.job_execution_get")
    def test_check_for_zombie_proxy_users(self, mock_conductor_je_get,
                                          mock_user_delete,
                                          mock_users_list):
        user_0 = mock.MagicMock()
        user_0.name = "admin"
        user_0.id = 0

        user_1 = mock.MagicMock()
        user_1.name = "job_0"
        user_1.id = 1

        user_2 = mock.MagicMock()
        user_2.name = "job_1"
        user_2.id = 2

        mock_users_list.return_value = [user_0, user_1, user_2]

        je_0 = mock.MagicMock()
        je_0.id = 0
        je_0.info = {"status": "KILLED"}

        je_1 = mock.MagicMock()
        je_1.id = 1
        je_1.info = {"status": "WAITING"}

        mock_conductor_je_get.side_effect = [je_0, je_1]

        p._make_periodic_tasks().check_for_zombie_proxy_users(None)

        mock_user_delete.assert_called_once_with(user_id=1)

    @mock.patch(
        'sahara.service.health.verification_base.validate_verification_start')
    @mock.patch('sahara.service.api.v10.update_cluster')
    def test_run_verifications_executed(self, cluster_update, ver_valid):
        self._make_cluster('1')
        p._make_periodic_tasks().run_verifications(None)
        self.assertEqual(1, ver_valid.call_count)
        cluster_update.assert_called_once_with(
            '1', {'verification': {'status': 'START'}})

    @mock.patch(
        'sahara.service.health.verification_base.validate_verification_start')
    @mock.patch('sahara.service.api.v10.update_cluster')
    def test_run_verifications_not_executed(self, cluster_update, ver_valid):
        self._make_cluster('1', status=c_u.CLUSTER_STATUS_ERROR)
        p._make_periodic_tasks().run_verifications(None)
        ver_valid.assert_not_called()
        cluster_update.assert_not_called()

    @mock.patch("sahara.service.periodic.threadgroup")
    @mock.patch("sahara.service.periodic.CONF")
    def test_setup_enabled(self, mock_conf, mock_thread_group):
        mock_conf.periodic_enable = True
        mock_conf.periodic_fuzzy_delay = 20
        mock_conf.periodic_interval_max = 30
        mock_conf.periodic_workers_number = 1
        mock_conf.periodic_coordinator_backend_url = ''

        add_timer = mock_thread_group.ThreadGroup().add_dynamic_timer

        p.setup()

        self.assertTrue(add_timer._mock_called)

    @mock.patch("sahara.service.periodic.threadgroup")
    @mock.patch("sahara.service.periodic.CONF")
    def test_setup_disabled(self, mock_conf, mock_thread_group):
        mock_conf.periodic_enable = False

        add_timer = mock_thread_group.ThreadGroup().add_dynamic_timer

        p.setup()

        self.assertFalse(add_timer._mock_called)

    def _make_cluster(self, id_name, status=c_u.CLUSTER_STATUS_ACTIVE,

                      is_transient=True):
        ctx = context.ctx()

        c = tc.SAMPLE_CLUSTER.copy()
        c["is_transient"] = is_transient
        c["status"] = status
        c["id"] = id_name
        c["name"] = id_name
        c['updated_at'] = timeutils.utcnow()
        c['trust_id'] = 'DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF'
        self.api.cluster_create(ctx, c)

    def _create_job_execution(self, values, job, input, output):
        values.update({"job_id": job['id'],
                       "input_id": input['id'],
                       "output_id": output['id']})
        self.api.job_execution_create(context.ctx(), values)
