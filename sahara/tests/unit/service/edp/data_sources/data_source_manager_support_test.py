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

import sahara.exceptions as ex
from sahara.service.edp.data_sources import manager as ds_manager
from sahara.tests.unit import base


class DataSourceManagerSupportTest(base.SaharaTestCase):

    def setUp(self):
        super(DataSourceManagerSupportTest, self).setUp()
        ds_manager.setup_data_sources()

    def test_data_sources_loaded(self):
        ds_types = [ds.name for ds in
                    ds_manager.DATA_SOURCES.get_data_sources()]

        self.assertIn('hdfs', ds_types)
        self.assertIn('manila', ds_types)
        self.assertIn('maprfs', ds_types)
        self.assertIn('swift', ds_types)

    def test_get_data_source_by_url(self):

        with testtools.ExpectedException(ex.InvalidDataException):
            ds_manager.DATA_SOURCES.get_data_source_by_url('')

        with testtools.ExpectedException(ex.InvalidDataException):
            ds_manager.DATA_SOURCES.get_data_source_by_url('hdfs')

        self.assertEqual('hdfs', ds_manager.DATA_SOURCES
                         .get_data_source_by_url('hdfs://').name)

        self.assertEqual('manila', ds_manager.DATA_SOURCES
                         .get_data_source_by_url('manila://').name)

        self.assertEqual('maprfs', ds_manager.DATA_SOURCES
                         .get_data_source_by_url('maprfs://').name)

        self.assertEqual('swift', ds_manager.DATA_SOURCES
                         .get_data_source_by_url('swift://').name)

    def test_get_data_source(self):

        with testtools.ExpectedException(ex.InvalidDataException):
            ds_manager.DATA_SOURCES.get_data_source('')

        with testtools.ExpectedException(ex.InvalidDataException):
            ds_manager.DATA_SOURCES.get_data_source('hdf')

        self.assertEqual('hdfs', ds_manager.DATA_SOURCES
                         .get_data_source('hdfs').name)

        self.assertEqual('manila', ds_manager.DATA_SOURCES
                         .get_data_source('manila').name)

        self.assertEqual('maprfs', ds_manager.DATA_SOURCES
                         .get_data_source('maprfs').name)

        self.assertEqual('swift', ds_manager.DATA_SOURCES
                         .get_data_source('swift').name)
