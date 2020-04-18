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

import testtools
from unittest import mock

import sahara.exceptions as ex
from sahara.service.edp.data_sources.hdfs.implementation import HDFSType
from sahara.tests.unit import base


class TestHDFSType(base.SaharaTestCase):
    def setUp(self):
        super(TestHDFSType, self).setUp()
        self.hdfs_type = HDFSType()

    def test_hdfs_type_validation_wrong_schema(self):
        data = {
            "name": "test_data_data_source",
            "url": "hdf://test_cluster/",
            "type": "hdfs",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.hdfs_type.validate(data)

    def test_hdfs_type_validation_correct_url(self):
        data = {
            "name": "test_data_data_source",
            "url": "hdfs://test_cluster/",
            "type": "hdfs",
            "description": "correct url schema"
        }
        self.hdfs_type.validate(data)

    def test_hdfs_type_validation_local_rel_url(self):
        data = {
            "name": "test_data_data_source",
            "url": "mydata/input",
            "type": "hdfs",
            "description": "correct url schema for relative path on local hdfs"
        }
        self.hdfs_type.validate(data)

    def test_hdfs_type_validation_local_abs_url(self):
        data = {
            "name": "test_data_data_source",
            "url": "/tmp/output",
            "type": "hdfs",
            "description": "correct url schema for absolute path on local hdfs"
        }
        self.hdfs_type.validate(data)

    @mock.patch('sahara.service.edp.data_sources.hdfs.implementation.h')
    def test_prepare_cluster(self, mock_h):
        cluster = mock.Mock()
        data_source = mock.Mock()
        runtime_url = "runtime_url"
        mock_h.configure_cluster_for_hdfs = mock.Mock()

        self.hdfs_type.prepare_cluster(data_source, cluster,
                                       runtime_url=runtime_url)

        mock_h.configure_cluster_for_hdfs.assert_called_once_with(cluster,
                                                                  runtime_url)
