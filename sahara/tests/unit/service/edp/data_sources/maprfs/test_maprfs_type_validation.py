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
from sahara.service.edp.data_sources.maprfs.implementation import MapRFSType
from sahara.tests.unit import base


class TestMapRFSTypeValidation(base.SaharaTestCase):
    def setUp(self):
        super(TestMapRFSTypeValidation, self).setUp()
        self.maprfs_type = MapRFSType()

    def test_maprfs_type_validation_wrong_schema(self):
        data = {
            "name": "test_data_data_source",
            "url": "maprf://test_cluster/",
            "type": "maprfs",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.maprfs_type.validate(data)

    def test_maprfs_type_validation_correct_url(self):
        data = {
            "name": "test_data_data_source",
            "url": "maprfs:///test_cluster/",
            "type": "maprfs",
            "description": "correct url schema"
        }
        self.maprfs_type.validate(data)

    def test_maprfs_type_validation_local_rel_url(self):
        data = {
            "name": "test_data_data_source",
            "url": "mydata/input",
            "type": "maprfs",
            "description": ("correct url schema for"
                            " relative path on local maprfs")
        }
        self.maprfs_type.validate(data)

    def test_maprfs_type_validation_local_abs_url(self):
        data = {
            "name": "test_data_data_source",
            "url": "/tmp/output",
            "type": "maprfs",
            "description": ("correct url schema for"
                            " absolute path on local maprfs")
        }
        self.maprfs_type.validate(data)
