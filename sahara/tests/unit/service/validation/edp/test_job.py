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

from sahara import exceptions as ex
from sahara.service.validations.edp import job as j
from sahara.service.validations.edp import job_schema as j_schema
from sahara.tests.unit.service.validation import utils as u
from sahara.utils import edp


class TestJobCreateValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestJobCreateValidation, self).setUp()
        self._create_object_fun = j.check_mains_libs
        self.scheme = j_schema.JOB_SCHEMA

    def test_bad_job_type_rejected(self):
        self._assert_create_object_validation(
            data={
                "name": "jar.jar",
                "type": "Jar",
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "type: 'Jar' is not one of " + str(edp.JOB_TYPES_ALL)))

    @mock.patch('sahara.service.api.v11.get_job_binary')
    def test_check_binaries(self, get_job_binary):
        get_job_binary.return_value = "value"
        j._check_binaries(["one", "two"])

        get_job_binary.return_value = None
        self.assertRaises(ex.NotFoundException,
                          j._check_binaries,
                          ["one", "two"])

    def test_mains_required_libs_optional(self):
        msg = "%s flow requires main script"
        spark_msg = "%s job requires main application jar"
        values = ((edp.JOB_TYPE_PIG, msg),
                  (edp.JOB_TYPE_HIVE, msg),
                  (edp.JOB_TYPE_SPARK, spark_msg))

        for job_type, msg in values:
            self._test_mains_required_libs_optional(job_type,
                                                    msg % job_type)

    def test_no_mains_libs_required(self):
        for job_type in (edp.JOB_TYPE_JAVA, edp.JOB_TYPE_MAPREDUCE):
            self._test_no_mains_libs_required(job_type)

    def test_no_mains_libs_optional(self):
        for job_type in (edp.JOB_TYPE_MAPREDUCE_STREAMING,):
            self._test_no_mains_libs_optional(job_type)

    @mock.patch('sahara.service.validations.edp.job._check_binaries')
    def _test_mains_required_libs_optional(self, job_type, no_mains_msg,
                                           _check_binaries):
        libs = ["lib1", "lib2"]
        mains = ["main"]

        # No mains, should raise an exception
        data = {
            "name": "job",
            "type": job_type,
            "libs": libs
        }
        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA", no_mains_msg))

        # Mains and libs overlap, should raise an exception
        data = {
            "name": "job",
            "type": job_type,
            "libs": libs,
            "mains": libs[1:]
        }
        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA",
                                  "'mains' and 'libs' overlap"))

        # Everything is okay, mains and libs
        data = {
            "name": "job",
            "type": job_type,
            "libs": libs,
            "mains": mains
        }
        self._assert_create_object_validation(data=data)
        _check_binaries._assert_called_with(data["libs"])
        _check_binaries._assert_called_with(data["mains"])
        _check_binaries.reset_mock()

        # Everything is okay, just mains
        data = {
            "name": "job",
            "type": job_type,
            "libs": [],
            "mains": mains
        }
        self._assert_create_object_validation(data=data)
        _check_binaries._assert_called_with(data["libs"])
        _check_binaries._assert_called_with(data["mains"])

    @mock.patch('sahara.service.validations.edp.job._check_binaries')
    def _test_no_mains_libs_required(self, job_type, _check_binaries):
        libs = ["lib1", "lib2"]
        mains = ["main"]

        # Just mains, should raise an exception
        data = {
            "name": "job",
            "type": job_type,
            "libs": [],
            "mains": mains
        }
        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA",
                                  "%s flow requires libs" % job_type))

        # Libs and mains, should raise an exception
        data = {
            "name": "job",
            "type": job_type,
            "libs": libs,
            "mains": mains
        }
        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA",
                                  "%s flow does not use mains" % job_type))

        # Everything is okay, libs but no mains
        data = {
            "name": "job",
            "type": job_type,
            "libs": libs,
            "mains": []
        }
        self._assert_create_object_validation(data=data)
        _check_binaries._assert_called_with(data["libs"])
        _check_binaries._assert_called_with(data["mains"])

    @mock.patch('sahara.service.validations.edp.job._check_binaries')
    def _test_no_mains_libs_optional(self, job_type, _check_binaries):
        libs = ["lib1", "lib2"]
        mains = ["main"]

        # Just mains, should raise an exception
        data = {
            "name": "job",
            "type": job_type,
            "libs": [],
            "mains": mains
        }
        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA",
                                  "%s flow does not use mains" % job_type))

        # Libs and mains, should raise an exception
        data = {
            "name": "job",
            "type": job_type,
            "libs": libs,
            "mains": mains
        }
        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA",
                                  "%s flow does not use mains" % job_type))

        # Everything is okay, libs but no mains
        data = {
            "name": "job",
            "type": job_type,
            "libs": libs,
            "mains": []
        }
        self._assert_create_object_validation(data=data)
        _check_binaries._assert_called_with(data["libs"])
        _check_binaries._assert_called_with(data["mains"])
        _check_binaries.reset_mock()

        # Everything is okay, no libs or mains
        data = {
            "name": "job",
            "type": job_type,
            "libs": [],
            "mains": []
        }
        self._assert_create_object_validation(data=data)
        _check_binaries._assert_called_with(data["libs"])
        _check_binaries._assert_called_with(data["mains"])


class TestJobUpdateValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestJobUpdateValidation, self).setUp()
        self._create_object_fun = mock.Mock()
        self.scheme = j_schema.JOB_UPDATE_SCHEMA

    def test_job_update_types(self):
        self._assert_types({
            'name': 'job',
            'description': 'very fast job'
        })

    def test_job_update_nothing_required(self):
        self._assert_create_object_validation(
            data={}
        )

    def test_job_update(self):
        data = {
            'name': 'job',
            'description': 'very fast job',
            'is_public': False,
            'is_protected': False
        }
        self._assert_types(data)

        self._assert_create_object_validation(data=data)

        self._assert_create_object_validation(
            data={
                'name': 'job',
                'id': '1'
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "Additional properties are not allowed "
                       "('id' was unexpected)")
        )
