# Copyright (c) 2013 Red Hat Inc.
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
import six

from sahara.service.validations.edp import job_executor as je
from sahara.tests.unit.service.validation import utils as u


def wrap_it(data):
    je.check_job_executor(data, 0)


class FakeJob(object):
    type = "Java"
    libs = []


class TestJobExecValidation(u.ValidationTestCase):

    def setUp(self):
        self._create_object_fun = wrap_it
        self.scheme = je.JOB_EXEC_SCHEMA

    @mock.patch('sahara.service.validations.base.check_edp_job_support')
    @mock.patch('sahara.service.validations.base.check_cluster_exists')
    @mock.patch('sahara.service.edp.api.get_job')
    def test_java(self, get_job, check_cluster, check_oozie):
        check_cluster.return_value = True
        check_oozie.return_value = None
        get_job.return_value = FakeJob()

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "job_configs": {"configs": {},
                                "params": {},
                                "args": []}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "Java job must "
                          "specify edp.java.main_class"))

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": "org.me.myclass"},
                    "params": {},
                    "args": []}
            })
