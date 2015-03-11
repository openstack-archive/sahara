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

from tempest.scenario.data_processing.client_tests import base
from tempest import test
from tempest_lib.common.utils import data_utils


class JobBinariesTest(base.BaseDataProcessingTest):
    def _check_job_binary_create(self, binary_body):
        binary_name = data_utils.rand_name('sahara-job-binary')

        # create job binary
        resp_body = self.create_job_binary(binary_name, **binary_body)

        # ensure that binary created successfully
        self.assertEqual(binary_name, resp_body.name)
        if 'swift' in binary_body['url']:
            binary_body = self.swift_job_binary
        else:
            binary_body = self.internal_db_binary
        self.assertDictContainsSubset(binary_body, resp_body.__dict__)

        return resp_body.id, binary_name

    def _check_job_binary_list(self, binary_id, binary_name):
        # check for job binary in list
        binary_list = self.client.job_binaries.list()
        binaries_info = [(binary.id, binary.name) for binary in binary_list]
        self.assertIn((binary_id, binary_name), binaries_info)

    def _check_job_binary_delete(self, binary_id):
        # delete job binary by id
        self.client.job_binaries.delete(binary_id)
        # check that job binary really deleted
        binary_list = self.client.job_binaries.list()
        self.assertNotIn(binary_id, [binary.id for binary in binary_list])

    def _check_swift_job_binary_create(self):
        self.swift_job_binary_with_extra = {
            'url': 'swift://sahara-container/example.jar',
            'description': 'Test job binary',
            'extra': {
                'user': 'test',
                'password': '123'
            }
        }
        # Create extra self.swift_job_binary variable to use for comparison to
        # job binary response body because response body has no 'extra' field.
        self.swift_job_binary = self.swift_job_binary_with_extra.copy()
        del self.swift_job_binary['extra']
        return self._check_job_binary_create(self.swift_job_binary_with_extra)

    def _check_swift_job_binary_get(self, binary_id, binary_name):
        # check job binary fetch by id
        binary = self.client.job_binaries.get(binary_id)
        self.assertEqual(binary_name, binary.name)
        self.assertDictContainsSubset(self.swift_job_binary, binary.__dict__)

    def _check_internal_db_job_binary_create(self):
        name = data_utils.rand_name('sahara-internal-job-binary')
        self.job_binary_data = 'Some data'
        job_binary_internal = (
            self.create_job_binary_internal(name, self.job_binary_data))
        self.internal_db_binary_with_extra = {
            'url': 'internal-db://%s' % job_binary_internal.id,
            'description': 'Test job binary',
            'extra': {
                'user': 'test',
                'password': '123'
            }
        }
        # Create extra self.internal_db_binary variable to use for comparison
        # to job binary response body because response body has no 'extra'
        # field.
        self.internal_db_binary = self.internal_db_binary_with_extra.copy()
        del self.internal_db_binary['extra']
        return self._check_job_binary_create(
            self.internal_db_binary_with_extra)

    def _check_internal_db_job_binary_get(self, binary_id, binary_name):
        # check job binary fetch by id
        binary = self.client.job_binaries.get(binary_id)
        self.assertEqual(binary_name, binary.name)
        self.assertDictContainsSubset(self.internal_db_binary, binary.__dict__)

    def _check_job_binary_get_file(self, binary_id):
        data = self.client.job_binaries.get_file(binary_id)
        self.assertEqual(self.job_binary_data, data)

    @test.services('data_processing')
    def test_swift_job_binaries(self):
        binary_id, binary_name = self._check_swift_job_binary_create()
        self._check_job_binary_list(binary_id, binary_name)
        self._check_swift_job_binary_get(binary_id, binary_name)
        self._check_job_binary_delete(binary_id)

    @test.services('data_processing')
    def test_internal_job_binaries(self):
        binary_id, binary_name = self._check_internal_db_job_binary_create()
        self._check_job_binary_list(binary_id, binary_name)
        self._check_internal_db_job_binary_get(binary_id, binary_name)
        self._check_job_binary_get_file(binary_id)
        self._check_job_binary_delete(binary_id)
