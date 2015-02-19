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

import mock
from oslo_utils import timeutils

from sahara.conductor import manager
from sahara import context
import sahara.service.periodic as p
import sahara.tests.unit.base as base
from sahara.tests.unit.conductor.manager import test_clusters as tc
from sahara.tests.unit.conductor.manager import test_edp as te


class TestPeriodicBack(base.SaharaWithDbTestCase):

    def setUp(self):
        super(TestPeriodicBack, self).setUp()
        self.api = manager.ConductorManager()

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
        self.assertEqual(get_job_status.call_count, 2)
        get_job_status.assert_has_calls([mock.call(u'2'),
                                         mock.call(u'3')])

    @mock.patch('sahara.service.ops.terminate_cluster')
    def test_transient_cluster_terminate(self, terminate_cluster):

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
        self.assertEqual(terminate_cluster.call_count, 1)
        terminate_cluster.assert_has_calls([mock.call(u'1')])

    @mock.patch('sahara.service.ops.terminate_cluster')
    def test_transient_cluster_not_killed_too_early(self, terminate_cluster):

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1')

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=20))

        p._make_periodic_tasks().terminate_unneeded_transient_clusters(None)
        self.assertEqual(terminate_cluster.call_count, 0)

    @mock.patch('sahara.service.ops.terminate_cluster')
    def test_transient_cluster_killed_in_time(self, terminate_cluster):

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1')

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=40))

        p._make_periodic_tasks().terminate_unneeded_transient_clusters(None)
        self.assertEqual(terminate_cluster.call_count, 1)
        terminate_cluster.assert_has_calls([mock.call(u'1')])

    @mock.patch('sahara.service.ops.terminate_cluster')
    def test_incomplete_cluster_not_killed_too_early(self, terminate_cluster):

        self.override_config('cleanup_time_for_incomplete_clusters', 1)

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1', status='Pending')

        timeutils.set_time_override(datetime.datetime(
            2005, 2, 1, minute=59, second=50))

        p._make_periodic_tasks().terminate_incomplete_clusters(None)
        self.assertEqual(terminate_cluster.call_count, 0)

    @mock.patch('sahara.service.ops.terminate_cluster')
    def test_incomplete_cluster_killed_in_time(self, terminate_cluster):

        self.override_config('cleanup_time_for_incomplete_clusters', 1)
        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1', status='Pending')

        timeutils.set_time_override(datetime.datetime(
            2005, 2, 1, hour=1, second=10))

        p._make_periodic_tasks().terminate_incomplete_clusters(None)
        self.assertEqual(terminate_cluster.call_count, 1)
        terminate_cluster.assert_has_calls([mock.call(u'1')])

    @mock.patch('sahara.service.ops.terminate_cluster')
    def test_active_cluster_not_killed_as_inactive(
            self, terminate_cluster):
        self.override_config('cleanup_time_for_incomplete_clusters', 1)

        timeutils.set_time_override(datetime.datetime(2005, 2, 1, second=0))

        self._make_cluster('1')

        timeutils.set_time_override(datetime.datetime(
            2005, 2, 1, hour=1, second=10))

        p._make_periodic_tasks().terminate_incomplete_clusters(None)
        self.assertEqual(terminate_cluster.call_count, 0)

    def _make_cluster(self, id_name, status='Active'):
        ctx = context.ctx()

        c = tc.SAMPLE_CLUSTER.copy()
        c["status"] = status
        c["id"] = id_name
        c["name"] = id_name
        c['updated_at'] = timeutils.utcnow()
        self.api.cluster_create(ctx, c)

    def _create_job_execution(self, values, job, input, output):
        values.update({"job_id": job['id'],
                       "input_id": input['id'],
                       "output_id": output['id']})
        self.api.job_execution_create(context.ctx(), values)
