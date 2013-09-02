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

from oslo.config import cfg

from savanna import context
import savanna.service.periodic as p
import savanna.tests.unit.conductor.base as test_base
from savanna.tests.unit.conductor.manager import test_clusters as tc
from savanna.tests.unit.conductor.manager import test_edp as te

CONF = cfg.CONF


class TestPeriodicBack(test_base.ConductorManagerTestCase):
    @mock.patch('savanna.service.edp.job_manager.get_job_status')
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
        p.SavannaPeriodicTasks().update_job_statuses(None)
        get_job_status.assert_has_calls([mock.call(u'2'),
                                         mock.call(u'3')])

    @mock.patch('savanna.service.edp.job_manager.get_job_status')
    @mock.patch('savanna.service.api.terminate_cluster')
    def test_cluster_terminate(self, terminate_cluster, get_job_status):
        CONF.use_identity_api_v3 = True
        ctx = context.ctx()
        job = self.api.job_create(ctx, te.SAMPLE_JOB)
        ds = self.api.data_source_create(ctx, te.SAMPLE_DATA_SOURCE)
        c = tc.SAMPLE_CLUSTER.copy()
        c["status"] = "Active"
        c["id"] = "1"
        c["name"] = "1"
        self.api.cluster_create(ctx, c)
        c["id"] = "2"
        c["name"] = "2"
        self.api.cluster_create(ctx, c)
        self._create_job_execution({"end_time": datetime.datetime.now(),
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
        p.SavannaPeriodicTasks().terminate_unneeded_clusters(None)
        self.assertEqual(1, len(terminate_cluster.call_args_list))
        terminated_cluster_id = terminate_cluster.call_args_list[0][0][0]
        self.assertEqual('1', terminated_cluster_id)

    def _create_job_execution(self, values, job, input, output):
        values.update({"job_id": job['id'],
                       "input_id": input['id'],
                       "output_id": output['id']})
        self.api.job_execution_create(context.ctx(), values)
