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

from savanna.service.validations.edp import job_executor as je
from savanna.tests.unit.service.validation import utils as u


def wrap_it(data):
    je.check_job_executor(data, 0)


class FakeJob(object):
    type = "MapReduce"
    libs = []


class TestJobExecValidation(u.ValidationTestCase):

    def setUp(self):
        self._create_object_fun = wrap_it
        self.scheme = je.JOB_EXEC_SCHEMA

    @mock.patch('savanna.service.validations.base.check_cluster_exists')
    @mock.patch('savanna.service.validations'
                '.edp.base.check_data_source_exists')
    @mock.patch('savanna.service.edp.api.get_job')
    def test_streaming(self, get_job, check_data, check_cluster):
        check_cluster.return_value = True
        check_data.return_value = True
        get_job.return_value = FakeJob()

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "input_id": six.text_type(uuid.uuid4()),
                "output_id": six.text_type(uuid.uuid4()),
                "job_configs": {"configs": {},
                                "params": {},
                                "args": []}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "MapReduce job without libs "
                          "must specify streaming mapper "
                          "and reducer"))

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "input_id": six.text_type(uuid.uuid4()),
                "output_id": six.text_type(uuid.uuid4()),
                "job_configs": {
                    "configs": {
                        "edp.streaming.mapper": "/bin/cat",
                        "edp.streaming.reducer": "/usr/bin/wc"},
                    "params": {},
                    "args": []}
            })
