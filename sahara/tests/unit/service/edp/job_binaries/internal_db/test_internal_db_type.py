# Copyright (c) 2017 OpenStack Foundation
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

from oslo_utils import uuidutils
import testtools

from sahara import exceptions as ex
from sahara.service.edp.job_binaries.internal_db import implementation


class TestInternalDBType(testtools.TestCase):

    def setUp(self):
        super(TestInternalDBType, self).setUp()
        self.internal_db = implementation.InternalDBType()

    def test_validate_job_location_format(self):

        self.assertFalse(self.internal_db.
                         validate_job_location_format(''))
        self.assertFalse(self.internal_db.
                         validate_job_location_format('invalid-scheme://'))
        self.assertFalse(self.internal_db.
                         validate_job_location_format('internal-db://abc'))
        self.assertTrue(self.internal_db.
                        validate_job_location_format(
                            'internal-db://' + uuidutils.generate_uuid()))

    @mock.patch('sahara.conductor.API.job_binary_internal_get_raw_data')
    def test_copy_binary_to_cluster(self, conductor_get_raw_data):
        remote = mock.Mock()
        context = mock.Mock()
        conductor_get_raw_data.return_value = 'ok'
        job_binary = mock.Mock()
        job_binary.name = 'test'
        job_binary.url = 'internal-db://somebinary'

        res = self.internal_db.copy_binary_to_cluster(job_binary,
                                                      context=context,
                                                      remote=remote)

        self.assertEqual('/tmp/test', res)
        remote.write_file_to.assert_called_with(
            '/tmp/test',
            'ok')

    @mock.patch('sahara.conductor.API.job_binary_internal_get_raw_data')
    def test_get_raw_data(self, conductor_get_raw_data):
        context = mock.Mock()
        conductor_get_raw_data.return_value = 'ok'
        job_binary = mock.Mock()
        job_binary.url = 'internal-db://somebinary'

        self.internal_db.get_raw_data(job_binary,
                                      context=context)

    @mock.patch('sahara.service.validations.edp.base.'
                'check_job_binary_internal_exists')
    def test_data_validation(self, check_exists):
        data = {
            'url': '',
            'description': 'empty url'
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.internal_db.validate(data)

        data = {
            'url': 'invalid-url://',
            'description': 'not empty, but invalid url'
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.internal_db.validate(data)

        data = {
            'url': 'internal-db://must-be-uuid',
            'description': 'correct scheme, but not netloc is not uuid'
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.internal_db.validate(data)

        data = {
            'url': 'internal-db://' + uuidutils.generate_uuid(),
            'description': 'correct scheme and netloc'
        }
        self.internal_db.validate(data)
