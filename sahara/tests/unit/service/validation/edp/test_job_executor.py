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

from sahara import main
from sahara.service import api
from sahara.service.validations.edp import job_execution as je
from sahara.tests.unit.service.validation import utils as u
from sahara.tests.unit import testutils as tu
from sahara.utils import edp


def wrap_it(data):
    je.check_job_execution(data, 0)


class TestJobExecValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestJobExecValidation, self).setUp()
        self._create_object_fun = wrap_it
        self.scheme = je.JOB_EXEC_SCHEMA
        # Make sure that the spark plugin is loaded
        if 'spark' not in main.CONF['plugins']:
            self.override_config('plugins', main.CONF['plugins'] + ['spark'])
        api.plugin_base.setup_plugins()

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.data_source_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_streaming(self, get_job, get_data_source, get_cluster):
        get_job.return_value = mock.Mock(
            type=edp.JOB_TYPE_MAPREDUCE_STREAMING, libs=[], interface=[])

        ds1_id = six.text_type(uuid.uuid4())
        ds2_id = six.text_type(uuid.uuid4())

        data_sources = {
            ds1_id: mock.Mock(type="swift", url="http://swift/test"),
            ds2_id: mock.Mock(type="swift", url="http://swift/test2"),
        }

        get_data_source.side_effect = lambda ctx, x: data_sources[x]

        ng = tu.make_ng_dict('master', 42, ['oozie'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        get_cluster.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "vanilla", "1.2.1", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "input_id": ds1_id,
                "output_id": ds2_id,
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
                "input_id": ds1_id,
                "output_id": ds2_id,
                "job_configs": {
                    "configs": {
                        "edp.streaming.mapper": "/bin/cat",
                        "edp.streaming.reducer": "/usr/bin/wc"},
                    "params": {},
                    "args": []}
            })

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.data_source_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_data_sources_differ(self, get_job, get_data_source, get_cluster):
        get_job.return_value = mock.Mock(
            type=edp.JOB_TYPE_MAPREDUCE_STREAMING, libs=[], interface=[])

        ds1_id = six.text_type(uuid.uuid4())
        ds2_id = six.text_type(uuid.uuid4())

        data_sources = {
            ds1_id: mock.Mock(type="swift", url="http://swift/test"),
            ds2_id: mock.Mock(type="swift", url="http://swift/test2"),
        }

        get_data_source.side_effect = lambda ctx, x: data_sources[x]

        ng = tu.make_ng_dict('master', 42, ['oozie'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        get_cluster.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "vanilla", "1.2.1", [ng])

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

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_check_edp_no_oozie(self, get_job, get_cluster):
        get_job.return_value = mock.Mock(type=edp.JOB_TYPE_PIG, libs=[],
                                         interface=[])

        ng = tu.make_ng_dict('master', 42, ['namenode'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        get_cluster.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "vanilla", "1.2.1", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "input_id": six.text_type(uuid.uuid4()),
                "output_id": six.text_type(uuid.uuid4())
            },
            bad_req_i=(1, "INVALID_COMPONENT_COUNT",
                       "Hadoop cluster should contain 1 oozie component(s). "
                       "Actual oozie count is 0"))

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_check_edp_job_support_spark(self, get_job, get_cluster):
        # utils.start_patch will construct a vanilla cluster as a
        # default for get_cluster, but we want a Spark cluster.
        # So, we'll make our own.

        # Note that this means we cannot use assert_create_object_validation()
        # because it calls start_patch() and will override our setting
        job = mock.Mock(type=edp.JOB_TYPE_SPARK, mains=["main"], interface=[])
        get_job.return_value = job
        ng = tu.make_ng_dict('master', 42, [], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        get_cluster.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "spark", "1.0.0", [ng])

        # Everything is okay, spark cluster supports EDP by default
        # because cluster requires a master and slaves >= 1
        wrap_it(data={"cluster_id": six.text_type(uuid.uuid4()),
                      "job_configs": {
                          "configs": {
                              "edp.java.main_class": "org.me.class"}}})

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_edp_main_class_java(self, job_get, cluster_get):
        job_get.return_value = mock.Mock(type=edp.JOB_TYPE_JAVA,
                                         interface=[])
        ng = tu.make_ng_dict('master', 42, ['namenode', 'oozie'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        cluster_get.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "vanilla", "1.2.1", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "job_configs": {"configs": {},
                                "params": {},
                                "args": []}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "%s job must "
                          "specify edp.java.main_class" % edp.JOB_TYPE_JAVA))

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": "org.me.myclass"},
                    "params": {},
                    "args": []}
            })

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_edp_main_class_spark(self, job_get, cluster_get):
        job_get.return_value = mock.Mock(type=edp.JOB_TYPE_SPARK,
                                         interface=[])
        ng = tu.make_ng_dict('master', 42, ['namenode'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        cluster_get.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "spark", "1.0.0", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "job_configs": {"configs": {},
                                "params": {},
                                "args": []}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "%s job must "
                          "specify edp.java.main_class" % edp.JOB_TYPE_SPARK))

        self._assert_create_object_validation(
            data={
                "cluster_id": six.text_type(uuid.uuid4()),
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": "org.me.myclass"},
                    "params": {},
                    "args": []}
            })
