# Copyright (c) 2017 Massachusetts Open Cloud
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

import testtools
from unittest import mock

from sahara import exceptions as ex
from sahara.service.edp.job_binaries.s3.implementation import S3Type
from sahara.tests.unit import base


class TestS3Type(base.SaharaTestCase):

    def setUp(self):
        super(TestS3Type, self).setUp()
        self.i_s = S3Type()

    @mock.patch('sahara.service.edp.job_binaries.s3.implementation.S3Type.'
                'get_raw_data')
    def test_copy_binary_to_cluster(self, get_raw_data):
        remote = mock.Mock()
        job_binary = mock.Mock()
        job_binary.name = 'test'
        job_binary.url = 's3://somebinary'
        get_raw_data.return_value = 'test'

        res = self.i_s.copy_binary_to_cluster(job_binary,
                                              remote=remote)

        self.assertEqual('/tmp/test', res)
        remote.write_file_to.assert_called_with(
            '/tmp/test',
            'test')

    def test_validate_job_location_format(self):
        self.assertTrue(
            self.i_s.validate_job_location_format("s3://temp/temp"))
        self.assertFalse(
            self.i_s.validate_job_location_format("s4://temp/temp"))
        self.assertFalse(self.i_s.validate_job_location_format("s3:///"))

    def test_validate(self):
        data = {"extra": {}, "url": "s3://temp/temp"}
        with testtools.ExpectedException(ex.InvalidDataException):
            self.i_s.validate(data)
        data["extra"] = {"accesskey": "a",
                         "secretkey": "s",
                         "endpoint": "e"}
        self.i_s.validate(data)
        data["extra"].pop("accesskey")
        with testtools.ExpectedException(ex.InvalidDataException):
            self.i_s.validate(data)

    @mock.patch('sahara.service.edp.s3_common.get_raw_job_binary_data')
    def test_get_raw_data(self, s3_get_raw_jbd):
        self.i_s.get_raw_data('a job binary')
        self.assertEqual(1, s3_get_raw_jbd.call_count)
