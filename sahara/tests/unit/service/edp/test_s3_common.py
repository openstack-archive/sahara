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
from sahara.service.edp import s3_common
from sahara.tests.unit import base


class FakeJB(object):
    extra = {"accesskey": "access",
             "secretkey": "my-secret",
             "endpoint": "pointy-end"}
    url = "s3://temp/temp"


class S3CommonTestCase(base.SaharaTestCase):

    @mock.patch("botocore.session.Session.create_client")
    @mock.patch("sahara.service.castellan.utils.get_secret")
    def test__get_s3_client(self, cast, boto):
        cast.return_value = "the-actual-password"
        je = FakeJB().extra
        s3_common._get_s3_client(je)
        args = ('s3', None, False, je['endpoint'], je['accesskey'],
                'the-actual-password')
        boto.called_once_with(*args)

    def test__get_names_from_job_binary_url(self):
        self.assertEqual(
            s3_common._get_names_from_job_binary_url("s3://buck"), ["buck"])
        self.assertEqual(
            s3_common._get_names_from_job_binary_url("s3://buck/obj"),
            ["buck", "obj"])
        self.assertEqual(
            s3_common._get_names_from_job_binary_url("s3://buck/dir/obj"),
            ["buck", "dir/obj"])

    def test__get_raw_job_binary_data(self):
        jb = mock.Mock()
        jb.url = "s3://bucket/object"
        boto_conn = mock.Mock()
        boto_conn.head_object = mock.Mock()
        boto_conn.get_object = mock.Mock()
        self.override_config('job_binary_max_KB', 1)

        boto_conn.head_object.return_value = {"ContentLength": 1025}
        self.assertRaises(ex.DataTooBigException,
                          s3_common._get_raw_job_binary_data,
                          jb, boto_conn)

        reader = mock.Mock()
        reader.read = lambda: "the binary"
        boto_conn.get_object.return_value = {"Body": reader}

        boto_conn.head_object.return_value = {"ContentLength": 1024}
        s3_common._get_raw_job_binary_data(jb, boto_conn)

        self.assertEqual(s3_common._get_raw_job_binary_data(jb, boto_conn),
                         "the binary")

        def _raiser():
            raise ValueError
        reader.read = _raiser
        self.assertRaises(ex.S3ClientException,
                          s3_common._get_raw_job_binary_data,
                          jb, boto_conn)

    def test__validate_job_binary_url(self):
        jb_url = "s3://bucket/object"
        s3_common._validate_job_binary_url(jb_url)
        jb_url = "s4://bucket/object"
        with testtools.ExpectedException(ex.BadJobBinaryException):
            s3_common._validate_job_binary_url(jb_url)
        jb_url = "s3://bucket"
        with testtools.ExpectedException(ex.BadJobBinaryException):
            s3_common._validate_job_binary_url(jb_url)

    @mock.patch("sahara.service.edp.s3_common._get_raw_job_binary_data")
    @mock.patch("sahara.service.edp.s3_common._get_s3_client")
    @mock.patch("sahara.service.edp.s3_common._validate_job_binary_url")
    def test_get_raw_job_binary_data(self, validate_jbu, get_s3cl, get_rjbd):
        get_s3cl.return_value = "this would have been boto"
        jb = FakeJB()
        s3_common.get_raw_job_binary_data(jb)
        validate_jbu.assert_called_once_with(jb.url)
        get_s3cl.assert_called_once_with(jb.extra)
        get_rjbd.assert_called_once_with(jb, "this would have been boto")
