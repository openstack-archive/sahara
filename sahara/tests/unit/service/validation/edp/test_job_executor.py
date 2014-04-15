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

from sahara.service import api
from sahara.service.validations import base as validation_base
from sahara.service.validations.edp import job_executor as je
from sahara.tests.unit.service.validation import utils as u
from sahara.tests.unit import testutils as tu


def wrap_it(data):
    je.check_job_executor(data, 0)


class FakeJob(object):
    type = "MapReduce.Streaming"
    libs = []


class TestJobExecValidation(u.ValidationTestCase):

    def setUp(self):
        self._create_object_fun = wrap_it
        self.scheme = je.JOB_EXEC_SCHEMA
        api.plugin_base.setup_plugins()

    @mock.patch('sahara.service.validations.edp.base.'
                'check_data_sources_are_different', lambda x, y: None)
    @mock.patch('sahara.service.validations.base.check_cluster_exists',
                lambda x: None)
    @mock.patch('sahara.service.validations.base.check_edp_job_support')
    @mock.patch('sahara.service.validations'
                '.edp.base.check_data_source_exists')
    @mock.patch('sahara.service.edp.api.get_job')
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
                          "MapReduce.Streaming job "
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

    @mock.patch('sahara.service.validations.base.check_cluster_exists',
                lambda x: None)
    @mock.patch('sahara.service.validations.base.check_edp_job_support',
                lambda x: None)
    @mock.patch('sahara.service.edp.api.get_data_source')
    @mock.patch('sahara.service.edp.api.get_job')
    def test_data_sources_differ(self, get_job, get_data_source):
        get_job.return_value = FakeJob()

        ds1_id = six.text_type(uuid.uuid4())
        ds2_id = six.text_type(uuid.uuid4())

        data_sources = {
            ds1_id: mock.Mock(type="swift", url="http://swift/test"),
            ds2_id: mock.Mock(type="swift", url="http://swift/test2"),
        }

        get_data_source.side_effect = lambda x: data_sources[x]

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "input_id": ds1_id,
                "output_id": ds2_id,
                "job_configs": {
                    "configs": {
                        "edp.streaming.mapper": "/bin/cat",
                        "edp.streaming.reducer": "/usr/bin/wc"},
                    "params": {},
                    "args": []}
            })

        data_sources[ds2_id].url = "http://swift/test"

        err_msg = ("Provided input and output DataSources reference the "
                   "same location: %s" % data_sources[ds2_id].url)

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "input_id": ds1_id,
                "output_id": ds2_id,
                "job_configs": {
                    "configs": {
                        "edp.streaming.mapper": "/bin/cat",
                        "edp.streaming.reducer": "/usr/bin/wc"},
                    "params": {},
                    "args": []}
            },
            bad_req_i=(1, "INVALID_DATA", err_msg))

    @mock.patch('sahara.service.api.get_cluster')
    @mock.patch('sahara.service.edp.api.get_job')
    def test_check_edp_job_support(self, get_job, get_cluster):
        get_job.return_value = FakeJob()
        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "input_id": six.text_type(uuid.uuid4()),
                "output_id": six.text_type(uuid.uuid4())
            },
            bad_req_i=(1, "INVALID_COMPONENT_COUNT",
                       "Hadoop cluster should contain 1 oozie components. "
                       "Actual oozie count is 0"))

        ng = tu.make_ng_dict('master', 42, ['oozie'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        get_cluster.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "vanilla", "1.2.1", [ng])
        validation_base.check_edp_job_support('some_id')
