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

from sahara.service.validations.edp import job as j
from sahara.tests.unit.service.validation import utils as u


class TestJobValidation(u.ValidationTestCase):

    def setUp(self):
        self._create_object_fun = j.check_mains_libs
        self.scheme = j.JOB_SCHEMA

    def test_empty_libs(self):
        for job_type in ['MapReduce', 'Java']:
            self._assert_create_object_validation(
                data={
                    "name": "jar.jar",
                    "type": job_type
                },
                bad_req_i=(1, "INVALID_DATA",
                           "%s flow requires libs" % job_type))

        self._assert_create_object_validation(
            data={
                "name": "jar.jar",
                "type": "MapReduce.Streaming",
            })

    def test_mains_unused(self):
        for job_type in ['MapReduce', 'Java']:
            self._assert_create_object_validation(
                data={
                    "name": "jar.jar",
                    "type": job_type,
                    "mains": ["lib1"],
                    "libs": ["lib2"]
                },
                bad_req_i=(1, "INVALID_DATA",
                           "%s flow does not use mains" % job_type))

    def test_empty_pig_mains(self):
        data = {
            "name": "pig.pig",
            "type": "Pig",
            "libs": ['lib-uuid']
        }

        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA",
                                  "Pig flow requires main script"))

        data.update({"type": "Hive"})

        self._assert_create_object_validation(
            data=data, bad_req_i=(1, "INVALID_DATA",
                                  "Hive flow requires main script"))

    def test_overlap_libs(self):
        for job_type in ['Hive', 'Pig']:
            self._assert_create_object_validation(
                data={
                    "name": "jar.jar",
                    "type": job_type,
                    "libs": ["lib1", "lib2"],
                    "mains": ["lib1"]
                },
                bad_req_i=(1, "INVALID_DATA", "'mains' and 'libs' overlap"))

    def test_jar_rejected(self):
        self._assert_create_object_validation(
            data={
                "name": "jar.jar",
                "type": "Jar",
            },
            bad_req_i=(1, "VALIDATION_ERROR",
                       "'Jar' is not one of "
                       "['Pig', 'Hive', 'MapReduce', "
                       "'MapReduce.Streaming', 'Java']"))
