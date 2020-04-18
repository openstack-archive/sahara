# Copyright (c) 2018 OpenStack Contributors
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

import sahara.exceptions as ex
from sahara.service.edp.data_sources.s3.implementation import S3Type
from sahara.tests.unit import base
from sahara.utils.types import FrozenDict


class TestSwiftType(base.SaharaTestCase):
    def setUp(self):
        super(TestSwiftType, self).setUp()
        self.s_type = S3Type()

    def test_validate(self):
        data = {
            "name": "test_data_data_source",
            "type": "s3",
            "url": "s3a://mybucket/myobject",
        }
        self.s_type.validate(data)

        data["url"] = "s3://mybucket/myobject"
        self.s_type.validate(data)

        creds = {}
        data["credentials"] = creds
        self.s_type.validate(data)

        creds["accesskey"] = "key"
        creds["secretkey"] = "key2"
        self.s_type.validate(data)

        creds["bucket_in_path"] = True
        creds["ssl"] = True
        creds["endpoint"] = "blah.org"
        self.s_type.validate(data)

        creds["cool_key"] = "wow"
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type.validate(data)

        creds.pop("cool_key")

        creds["ssl"] = "yeah"
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type.validate(data)

        creds["ssl"] = True
        creds["bucket_in_path"] = "yeah"
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type.validate(data)

    def test_validate_url(self):
        url = ""
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type._validate_url(url)
        url = "s3a://"
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type._validate_url(url)
        url = "s3a:///"
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type._validate_url(url)
        url = "s3a://bucket"
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type._validate_url(url)
        url = "s3b://bucket/obj"
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type._validate_url(url)
        url = "s3a://bucket/obj"
        self.s_type._validate_url(url)
        url = "s3a://bucket/fold/obj"
        self.s_type._validate_url(url)
        url = "s3a://bucket/obj/"
        self.s_type._validate_url(url)

    def test_prepare_cluster(self):
        ds = mock.Mock()
        cluster = mock.Mock()
        ds.credentials = {}
        job_configs = {}

        self.s_type.prepare_cluster(ds, cluster, job_configs=job_configs)
        self.assertEqual(job_configs, {})

        job_configs['configs'] = {}
        ds.credentials['accesskey'] = 'key'
        self.s_type.prepare_cluster(ds, cluster, job_configs=job_configs)
        self.assertEqual(job_configs['configs'], {'fs.s3a.access.key': 'key'})

        job_configs['configs'] = {'fs.s3a.access.key': 'key2'}
        self.s_type.prepare_cluster(ds, cluster, job_configs=job_configs)
        self.assertEqual(job_configs['configs'], {'fs.s3a.access.key': 'key2'})

        job_configs = FrozenDict({'configs': {}})
        self.s_type.prepare_cluster(ds, cluster, job_configs=job_configs)
        self.assertNotIn(job_configs['configs'], 'accesskey')

        job_configs = {}
        self.s_type.prepare_cluster(ds, cluster, job_configs=job_configs)
        self.assertEqual(job_configs, {})
