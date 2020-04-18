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

from unittest import mock

from sahara.service.api import v10 as api
from sahara.service.validations.edp import job_binary as b
from sahara.service.validations.edp.job_binary import jb_manager
from sahara.service.validations.edp import job_binary_schema as b_s
from sahara.swift import utils as su
from sahara.tests.unit.service.validation import utils as u


class TestJobBinaryValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestJobBinaryValidation, self).setUp()
        self._create_object_fun = b.check_job_binary
        self.scheme = b_s.JOB_BINARY_SCHEMA
        api.plugin_base.setup_plugins()
        jb_manager.setup_job_binaries()

    @mock.patch('sahara.utils.api_validator.jb_manager')
    def test_creation(self, mock_jb_manager):
        JOB_BINARIES = mock.Mock()
        mock_jb = mock.Mock()
        mock_jb_manager.JOB_BINARIES = JOB_BINARIES

        JOB_BINARIES.get_job_binary_by_url = mock.Mock(return_value=mock_jb)

        mock_jb.validate_job_location_format = mock.Mock(return_value=True)

        data = {
            "name": "main.jar",
            "url": "internal-db://3e4651a5-1f08-4880-94c4-596372b37c64",
            "extra": {
                "user": "user",
                "password": "password"
            },
            "description": "long description"
        }
        self._assert_types(data)

    @mock.patch('sahara.utils.api_validator.jb_manager')
    def test_job_binary_create_swift(self, mock_jb_manager):
        JOB_BINARIES = mock.Mock()
        mock_jb = mock.Mock()
        mock_jb_manager.JOB_BINARIES = JOB_BINARIES

        JOB_BINARIES.get_job_binary_by_url = mock.Mock(return_value=mock_jb)

        mock_jb.validate_job_location_format = mock.Mock(return_value=True)
        self._assert_create_object_validation(
            data={
                "name": "j_o_w",
                "url": su.SWIFT_INTERNAL_PREFIX + "o.sahara/k"
            },
            bad_req_i=(1, "BAD_JOB_BINARY",
                       "To work with JobBinary located in internal "
                       "swift add 'user' and 'password' to extra"))
        self.override_config('use_domain_for_proxy_users', True)
        self._assert_create_object_validation(
            data={
                "name": "j_o_w",
                "url": su.SWIFT_INTERNAL_PREFIX + "o.sahara/k"
            })

    @mock.patch('sahara.utils.api_validator.jb_manager')
    def test_job_binary_create_internal(self, mock_jb_manager):
        JOB_BINARIES = mock.Mock()
        mock_jb = mock.Mock()
        mock_jb_manager.JOB_BINARIES = JOB_BINARIES

        JOB_BINARIES.get_job_binary_by_url = mock.Mock(return_value=mock_jb)

        mock_jb.validate_job_location_format = mock.Mock(return_value=False)
        self._assert_create_object_validation(
            data={
                "name": "main.jar",
                "url": "internal-db://abacaba",
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "url: 'internal-db://abacaba' is not a "
                       "'valid_job_location'"))

    @mock.patch('sahara.utils.api_validator.jb_manager')
    def test_job_binary_create_manila(self, mock_jb_manager):
        JOB_BINARIES = mock.Mock()
        mock_jb = mock.Mock()
        mock_jb_manager.JOB_BINARIES = JOB_BINARIES

        JOB_BINARIES.get_job_binary_by_url = mock.Mock(return_value=mock_jb)

        mock_jb.validate_job_location_format = mock.Mock(return_value=False)
        self._assert_create_object_validation(
            data={
                "name": "main.jar",
                "url": "manila://abacaba",
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "url: 'manila://abacaba' is not a "
                       "'valid_job_location'"))
