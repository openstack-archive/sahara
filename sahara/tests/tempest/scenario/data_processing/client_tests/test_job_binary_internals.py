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


class JobBinaryInternalsTest(base.BaseDataProcessingTest):
    def _check_job_binary_internal_create(self):
        name = data_utils.rand_name('sahara-internal-job-binary')
        self.job_binary_data = 'Some data'
        # create job binary internal
        resp_body = self.create_job_binary_internal(name, self.job_binary_data)
        # check that job_binary_internal created successfully
        self.assertEqual(name, resp_body.name)
        return resp_body.id, resp_body.name

    def _check_job_binary_internal_list(self, binary_id, binary_name):
        # check for job binary internal in list
        binary_list = self.client.job_binary_internals.list()
        binaries_info = [(binary.id, binary.name) for binary in binary_list]
        self.assertIn((binary_id, binary_name), binaries_info)

    def _check_job_binary_internal_get(self, binary_id, binary_name):
        # check job binary internal fetch by id
        binary = self.client.job_binary_internals.get(binary_id)
        self.assertEqual(binary_name, binary.name)

    def _check_job_binary_internal_update(self, binary_id):
        values = {
            'name': data_utils.rand_name('sahara-internal-job-binary'),
            'is_public': True
        }
        binary = self.client.job_binary_internals.update(binary_id, **values)
        self.assertDictContainsSubset(values, binary.job_binary_internal)

    def _check_job_binary_internal_delete(self, binary_id):
        # delete job binary internal by id
        self.client.job_binary_internals.delete(binary_id)
        # check that job binary internal really deleted
        binary_list = self.client.job_binary_internals.list()
        self.assertNotIn(binary_id, [binary.id for binary in binary_list])

    @test.services('data_processing')
    def test_job_binary_internal(self):
        binary_id, binary_name = self._check_job_binary_internal_create()
        self._check_job_binary_internal_list(binary_id, binary_name)
        self._check_job_binary_internal_get(binary_id, binary_name)
        self._check_job_binary_internal_update(binary_id)
        self._check_job_binary_internal_delete(binary_id)
