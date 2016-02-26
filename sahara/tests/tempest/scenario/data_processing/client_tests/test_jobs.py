# Copyright (c) 2014 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.lib.common.utils import data_utils
from tempest import test

from sahara.tests.tempest.scenario.data_processing.client_tests import base


class JobTest(base.BaseDataProcessingTest):
    def _check_create_job(self):
        job_binary = {
            'name': data_utils.rand_name('sahara-job-binary'),
            'url': 'swift://sahara-container.sahara/example.jar',
            'description': 'Test job binary',
            'extra': {
                'user': 'test',
                'password': '123'
            }
        }
        # create job_binary
        job_binary = self.create_job_binary(**job_binary)

        self.job = {
            'job_type': 'Pig',
            'mains': [job_binary.id]
        }
        job_name = data_utils.rand_name('sahara-job')
        # create job
        job = self.create_job(job_name, **self.job)
        # check that job created successfully
        self.assertEqual(job_name, job.name)

        return job.id, job.name

    def _check_job_list(self, job_id, job_name):
        # check for job in list
        job_list = self.client.jobs.list()
        jobs_info = [(job.id, job.name) for job in job_list]
        self.assertIn((job_id, job_name), jobs_info)

    def _check_get_job(self, job_id, job_name):
        # check job fetch by id
        job = self.client.jobs.get(job_id)
        self.assertEqual(job_name, job.name)

    def _check_job_update(self, job_id):
        # check updating of job
        values = {
            'name': data_utils.rand_name('updated-sahara-job'),
            'description': 'description'

        }
        job = self.client.jobs.update(job_id, **values)
        self.assertDictContainsSubset(values, job.job)

    def _check_delete_job(self, job_id):
        # delete job by id
        self.client.jobs.delete(job_id)
        # check that job really deleted
        job_list = self.client.jobs.list()
        self.assertNotIn(job_id, [job.id for job in job_list])

    @test.services('data_processing')
    def test_job(self):
        job_id, job_name = self._check_create_job()
        self._check_job_list(job_id, job_name)
        self._check_get_job(job_id, job_name)
        self._check_job_update(job_id)
        self._check_delete_job(job_id)
