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

from oslo_utils import uuidutils
import testtools

import sahara.exceptions as ex
import sahara.service.edp.data_sources.manager as ds_manager
from sahara.service.validations.edp import data_source as ds
from sahara.tests.unit.service.validation import utils as u


class TestDataSourceUpdateValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestDataSourceUpdateValidation, self).setUp()
        ds_manager.setup_data_sources()

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

    def _update_manila(self):
        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'type': 'manila'}, 'ds_id')

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update(
                {"url": "manila://%s/foo" % uuidutils.generate_uuid()},
                'ds_id')

        ds.check_data_source_update(
            {'type': 'manila',
             'url': 'manila://%s/foo' % uuidutils.generate_uuid()}, 'ds_id')

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
    def test_update_data_source_name(self, ds_get, ds_all, je_all):
        ds1 = mock.Mock()
        ds1.name = 'ds1'
        ds_all.return_value = [ds1]
        ds.check_data_source_update({'name': 'ds', 'url': '/ds1'}, 'ds_id')

        ds1.name = 'ds'
        with testtools.ExpectedException(ex.NameAlreadyExistsException):
            ds.check_data_source_update({'name': 'ds', 'url': '/ds1'}, 'ds_id')

        ds_get.return_value = ds1
        ds.check_data_source_update({'name': 'ds', 'url': '/ds1'}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.conductor.API.data_source_get')
    def test_update_data_source_swift(self, ds_get, je_all):
        old_ds = mock.Mock(id='ds_id', type='swift', url='swift://cont/obj',
                           credentials={'user': 'user', 'password': 'pass'})
        ds_get.return_value = old_ds

        ds.check_data_source_update({'url': 'swift://cont/obj2'}, 'ds_id')

        self._update_hdfs()
        self._update_maprfs()
        self._update_manila()

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
        self._update_manila()

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
        self._update_manila()

        ds.check_data_source_update({'url': '/tmp/file'}, 'ds_id')

    @mock.patch('sahara.conductor.API.job_execution_get_all')
    @mock.patch('sahara.conductor.API.data_source_get')
    def test_update_data_source_manila(self, ds_get, je_all):
        old_ds = mock.Mock(id='ds_id', type='manila',
                           url='manila://%s/foo' % uuidutils.generate_uuid(),
                           credentials={})
        ds_get.return_value = old_ds

        ds.check_data_source_update(
            {'url': 'manila://%s/foo' % uuidutils.generate_uuid()}, 'ds_id')

        self._update_swift()
        self._update_hdfs()
        self._update_maprfs()

        with testtools.ExpectedException(ex.InvalidDataException):
            ds.check_data_source_update({'url': '/tmp/file'}, 'ds_id')

    def test_check_datasource_placeholder(self):
        with testtools.ExpectedException(ex.InvalidDataException):
            ds._check_datasource_placeholder("/tmp/%RANDSTR(-1)%")
        with testtools.ExpectedException(ex.InvalidDataException):
            ds._check_datasource_placeholder("/tmp/%RANDSTR(2345)%")
        with testtools.ExpectedException(ex.InvalidDataException):

            ds._check_datasource_placeholder(
                "/tmp/%RANDSTR(513)%-%RANDSTR(513)%")

        result = ds._check_datasource_placeholder("/tmp/%RANDSTR(42)%")
        self.assertIsNone(result)
