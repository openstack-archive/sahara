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

import uuid

import mock
import testtools

import sahara.exceptions as ex
from sahara.service import api
from sahara.service.validations.edp import data_source as ds
from sahara.service.validations.edp import data_source_schema as ds_schema
from sahara.swift import utils as su
from sahara.tests.unit.service.validation import utils as u

SAMPLE_SWIFT_URL = "swift://1234/object"
SAMPLE_SWIFT_URL_WITH_SUFFIX = "swift://1234%s/object" % su.SWIFT_URL_SUFFIX


class TestDataSourceCreateValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestDataSourceCreateValidation, self).setUp()
        self._create_object_fun = ds.check_data_source_create
        self.scheme = ds_schema.DATA_SOURCE_SCHEMA
        api.plugin_base.setup_plugins()

    def test_swift_creation(self):
        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "credentials": {
                "user": "user",
                "password": "password"
            },
            "description": "long description"
        }
        self._assert_types(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_missing_credentials(self,
                                                check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "description": "long description"
        }
        with testtools.ExpectedException(ex.InvalidCredentials):
            ds.check_data_source_create(data)
        # proxy enabled should allow creation without credentials
        self.override_config('use_domain_for_proxy_users', True)
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_credentials_missing_user(
            self,
            check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "credentials": {
                "password": "password"
            },
            "description": "long description"
        }
        with testtools.ExpectedException(ex.InvalidCredentials):
            ds.check_data_source_create(data)
        # proxy enabled should allow creation without credentials
        self.override_config('use_domain_for_proxy_users', True)
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_credentials_missing_password(
            self,
            check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "credentials": {
                "user": "user",
            },
            "description": "long description"
        }
        with testtools.ExpectedException(ex.InvalidCredentials):
            ds.check_data_source_create(data)
        # proxy enabled should allow creation without credentials
        self.override_config('use_domain_for_proxy_users', True)
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_wrong_schema(self, check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "swif://1234/object",
            "type": "swift",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_explicit_suffix(self,
                                            check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL_WITH_SUFFIX,
            "type": "swift",
            "description": "incorrect url schema",
            "credentials": {
                "user": "user",
                "password": "password"
            }
        }
        self._assert_types(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_wrong_suffix(self,
                                         check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "swift://1234.suffix/object",
            "type": "swift",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_missing_object(self,
                                           check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "swift://1234/",
            "type": "swift",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_hdfs_creation_wrong_schema(self, check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "hdf://test_cluster/",
            "type": "hdfs",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_hdfs_creation_correct_url(self, check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "hdfs://test_cluster/",
            "type": "hdfs",
            "description": "correct url schema"
        }
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_hdfs_creation_local_rel_url(self, check_data_source_unique_name):
        check_data_source_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "mydata/input",
            "type": "hdfs",
            "description": "correct url schema for relative path on local hdfs"
        }
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_hdfs_creation_local_abs_url(self, check_data_source_unique_name):
        check_data_source_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "/tmp/output",
            "type": "hdfs",
            "description": "correct url schema for absolute path on local hdfs"
        }
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_maprfs_creation_wrong_schema(self, check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "maprf://test_cluster/",
            "type": "maprfs",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_maprfs_creation_correct_url(self, check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "maprfs:///test_cluster/",
            "type": "maprfs",
            "description": "correct url schema"
        }
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_maprfs_creation_local_rel_url(self, check_ds_unique_name):
        check_ds_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "mydata/input",
            "type": "maprfs",
            "description": ("correct url schema for"
                            " relative path on local maprfs")
        }
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_maprfs_creation_local_abs_url(self, check_ds_unique_name):
        check_ds_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "/tmp/output",
            "type": "maprfs",
            "description": ("correct url schema for"
                            " absolute path on local maprfs")
        }
        ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_manila_creation_wrong_schema(self, check_ds_unique_name):
        check_ds_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "man://%s" % uuid.uuid4(),
            "type": "manila",
            "description": ("incorrect url schema for")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_manila_creation_empty_url(self, check_ds_unique_name):
        check_ds_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "",
            "type": "manila",
            "description": ("empty url")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_manila_creation_no_uuid(self, check_ds_unique_name):
        check_ds_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "manila://bob",
            "type": "manila",
            "description": ("netloc is not a uuid")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_manila_creation_no_path(self, check_ds_unique_name):
        check_ds_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "manila://%s" % uuid.uuid4(),
            "type": "manila",
            "description": ("netloc is not a uuid")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_manila_correct(self, check_ds_unique_name):
        check_ds_unique_name.return_value = True
        data = {
            "name": "test_data_data_source",
            "url": "manila://%s/foo" % uuid.uuid4(),
            "type": "manila",
            "description": ("correct url")
        }
        self._assert_types(data)


class TestDataSourceUpdateValidation(u.ValidationTestCase):
    def _update_swift(self):
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'url': 'swift://cont/obj'}, 'ds_id')

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'type': 'swift'}, 'ds_id')

        with testtools.ExpectedException(ex.InvalidCredentials):
            ds.check_data_source_update(
                {'type': 'swift', 'url': 'swift://cont/obj'}, 'ds_id')

        ds.check_data_source_update(
            {'type': 'swift', 'url': 'swift://cont/obj',
             'credentials': {'user': 'user', 'password': 'pass'}}, 'ds_id')

    def _update_hdfs(self):
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'url': 'hdfs://cl/data'}, 'ds_id')

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'type': 'hdfs'}, 'ds_id')

        ds.check_data_source_update(
            {'url': 'hdfs://cl/data', 'type': 'hdfs'}, 'ds_id')

    def _update_maprfs(self):
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'type': 'maprfs'}, 'ds_id')

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'url': 'maprfs://cluster'}, 'ds_id')

        ds.check_data_source_update(
            {'type': 'maprfs', 'url': 'maprfs://cluster'}, 'ds_id')

    def _update_manilla(self):
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'type': 'manila'}, 'ds_id')

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update(
                {"url": "manila://%s/foo" % uuid.uuid4()}, 'ds_id')

        ds.check_data_source_update(
            {'type': 'manila',
             'url': 'manila://%s/foo' % uuid.uuid4()}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    def test_update_referenced_data_source(self, je_all):
        je_all.return_value = [mock.Mock(
            info={"status": "PENDING"},
            data_source_urls={"ds_id": "ds_url"})]
        with testtools.ExpectedException(ex.UpdateFailedException):
            ds.check_data_source_update({'name': 'ds'}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.conductor.API.data_source_get_all')
    @mock.patch('sahara.conductor.API.data_source_get')
    def test_update_data_source_name(self, je_all, ds_all, ds_get):
        ds1 = mock.Mock()
        ds1.name = 'ds1'
        ds_all.return_value = [ds1]
        ds.check_data_source_update({'name': 'ds'}, 'ds_id')

        ds1.name = 'ds'
        with testtools.ExpectedException(ex.NameAlreadyExistsException):
            ds.check_data_source_update({'name': 'ds'}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.conductor.API.data_source_get')
    def test_update_data_source_swift(self, ds_get, je_all):
        old_ds = mock.Mock(id='ds_id', type='swift', url='swift://cont/obj',
                           credentials={'user': 'user', 'password': 'pass'})
        ds_get.return_value = old_ds

        ds.check_data_source_update({'url': 'swift://cont/obj2'}, 'ds_id')

        self._update_hdfs()
        self._update_maprfs()
        self._update_manilla()

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'url': '/tmp/file'}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.conductor.API.data_source_get')
    def test_update_data_source_hdfs(self, ds_get, je_all):
        old_ds = mock.Mock(id='ds_id', type='hdfs', url='hdfs://cl/data',
                           credentials={})
        ds_get.return_value = old_ds

        ds.check_data_source_update({'url': 'hdfs://cl/data1'}, 'ds_id')

        self._update_swift()
        self._update_maprfs()
        self._update_manilla()

        ds.check_data_source_update({'url': '/tmp/file'}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.conductor.API.data_source_get')
    def test_update_data_source_maprfs(self, ds_get, je_all):
        old_ds = mock.Mock(id='ds_id', type='maprfs', url='maprfs://cluster',
                           credentials={})
        ds_get.return_value = old_ds

        ds.check_data_source_update({'url': 'maprfs://cluster/data'}, 'ds_id')

        self._update_swift()
        self._update_hdfs()
        self._update_manilla()

        ds.check_data_source_update({'url': '/tmp/file'}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.conductor.API.data_source_get')
    def test_update_data_source_manila(self, ds_get, je_all):
        old_ds = mock.Mock(id='ds_id', type='manila',
                           url='manila://%s/foo' % uuid.uuid4(),
                           credentials={})
        ds_get.return_value = old_ds

        ds.check_data_source_update(
            {'url': 'manila://%s/foo' % uuid.uuid4()}, 'ds_id')

        self._update_swift()
        self._update_hdfs()
        self._update_maprfs()

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'url': '/tmp/file'}, 'ds_id')
