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

from sahara.service.api import v10 as api
from sahara.service.validations.edp import job_binary_internal as jb
from sahara.service.validations.edp.job_binary_internal import jb_manager
from sahara.service.validations.edp import job_binary_internal_schema as jbs
from sahara.tests.unit.service.validation import utils as u


class TestJobBinaryInternalCreateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestJobBinaryInternalCreateValidation, self).setUp()
        self._create_object_fun = jb.check_job_binary_internal
        api.plugin_base.setup_plugins()
        jb_manager.setup_job_binaries()

    def test_job_binary_internal_create(self):
        self._assert_create_object_validation(data=b'text')

        self._assert_create_object_validation(
            data='',
            bad_req_i=(1, "BAD_JOB_BINARY",
                       "Job binary internal data must be a string of length "
                       "greater than zero"))


class TestJobBinaryInternalUpdateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestJobBinaryInternalUpdateValidation, self).setUp()
        self._create_object_fun = mock.Mock()
        self.scheme = jbs.JOB_BINARY_UPDATE_SCHEMA

    def test_job_binary_internal_update_types(self):
        data = {
            'name': 'jb',
            'is_public': False,
            'is_protected': False
        }
        self._assert_types(data)

    def test_job_binary_internal_update(self):
        self._assert_create_object_validation(data={'name': 'jb'})

        self._assert_create_object_validation(
            data={'id': '1',
                  'is_public': False,
                  'is_protected': False},
            bad_req_i=(1, "VALIDATION_ERROR",
                       "Additional properties are not allowed "
                       "('id' was unexpected)"))
