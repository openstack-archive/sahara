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

import mock

import sahara.exceptions as ex
from sahara.service import api
from sahara.service.validations.edp import data_source as ds
from sahara.tests.unit.service.validation import utils as u


class TestDataSourceValidation(u.ValidationTestCase):
    def setUp(self):
        self._create_object_fun = ds.check_data_source_create
        self.scheme = ds.DATA_SOURCE_SCHEMA
        api.plugin_base.setup_plugins()

    def test_swift_creation(self):
        data = {
            "name": "test_data_data_source",
            "url": "swift://1234",
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
            "url": "swift://1234",
            "type": "swift",
            "description": "long description"
        }
        with self.assertRaises(ex.InvalidCredentials):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_credentials_missing_user(
            self,
            check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "swift://1234",
            "type": "swift",
            "credentials": {
                "password": "password"
            },
            "description": "long description"
        }
        with self.assertRaises(ex.InvalidCredentials):
            ds.check_data_source_create(data)

    @mock.patch("sahara.service.validations."
                "edp.base.check_data_source_unique_name")
    def test_swift_creation_credentials_missing_password(
            self,
            check_data_source_unique_name):
        check_data_source_unique_name.return_value = True

        data = {
            "name": "test_data_data_source",
            "url": "swift://1234",
            "type": "swift",
            "credentials": {
                "user": "user",
            },
            "description": "long description"
        }
        with self.assertRaises(ex.InvalidCredentials):
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
        with self.assertRaises(ex.InvalidException):
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
