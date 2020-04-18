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

import time
from unittest import mock

from oslo_utils import timeutils
from oslo_utils import uuidutils
import testtools

from sahara import exceptions as ex
from sahara.service.api import v10 as api
from sahara.service.validations.edp import job_execution as je
from sahara.service.validations.edp import job_execution_schema as je_schema
from sahara.tests.unit.service.validation import utils as u
from sahara.tests.unit import testutils as tu
from sahara.utils import edp


def wrap_it(data):
    je.check_job_execution(data, 0)


class TestJobExecCreateValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestJobExecCreateValidation, self).setUp()
        self._create_object_fun = wrap_it
        self.scheme = je_schema.JOB_EXEC_SCHEMA
        api.plugin_base.setup_plugins()

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.data_source_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_streaming(self, get_job, get_data_source, get_cluster):
        get_job.return_value = mock.Mock(
            type=edp.JOB_TYPE_MAPREDUCE_STREAMING, libs=[], interface=[])

        ds1_id = uuidutils.generate_uuid()
        ds2_id = uuidutils.generate_uuid()

        data_sources = {
            ds1_id: mock.Mock(type="swift", url="http://swift/test"),
            ds2_id: mock.Mock(type="swift", url="http://swift/test2"),
        }

        get_data_source.side_effect = lambda ctx, x: data_sources[x]

        ng = tu.make_ng_dict('master', 42, ['oozie'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        get_cluster.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "fake", "0.1", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "input_id": ds1_id,
                "output_id": ds2_id,
                "job_configs": {"configs": {},
                                "params": {},
                                "args": [],
                                "job_execution_info": {}}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "MapReduce.Streaming job "
                          "must specify streaming mapper "
                          "and reducer"))

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "input_id": ds1_id,
                "output_id": ds2_id,
                "job_configs": {
                    "configs": {
                        "edp.streaming.mapper": "/bin/cat",
                        "edp.streaming.reducer": "/usr/bin/wc"},
                    "params": {},
                    "job_execution_info": {},
                    "args": []}
            })

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    @mock.patch('sahara.conductor.api.LocalApi.data_source_get')
    @mock.patch('sahara.conductor.api.LocalApi.job_get')
    def test_data_sources_differ(self, get_job, get_data_source, get_cluster):
        get_job.return_value = mock.Mock(
            type=edp.JOB_TYPE_MAPREDUCE_STREAMING, libs=[], interface=[])

        ds1_id = uuidutils.generate_uuid()
        ds2_id = uuidutils.generate_uuid()

        data_sources = {
            ds1_id: mock.Mock(type="swift", url="http://swift/test"),
            ds2_id: mock.Mock(type="swift", url="http://swift/test2"),
        }

        get_data_source.side_effect = lambda ctx, x: data_sources[x]

        ng = tu.make_ng_dict('master', 42, ['oozie'], 1,
                             instances=[tu.make_inst_dict('id', 'name')])
        get_cluster.return_value = tu.create_cluster("cluster", "tenant1",
                                                     "fake", "0.1", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "input_id": ds1_id,
                "output_id": ds2_id,
                "job_configs": {
                    "configs": {
                        "edp.streaming.mapper": "/bin/cat",
                        "edp.streaming.reducer": "/usr/bin/wc"},
                    "params": {},
                    "job_execution_info": {},
                    "args": []}
            })

        data_sources[ds2_id].url = "http://swift/test"

        err_msg = ("Provided input and output DataSources reference the "
                   "same location: %s" % data_sources[ds2_id].url)

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "input_id": ds1_id,
                "output_id": ds2_id,
                "job_configs": {
                    "configs": {
                        "edp.streaming.mapper": "/bin/cat",
                        "edp.streaming.reducer": "/usr/bin/wc"},
                    "params": {},
                    "job_execution_info": {},
                    "args": []}
            },
            bad_req_i=(1, "INVALID_DATA", err_msg))

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
                                                     "fake", "0.1", [ng])

        # Everything is okay, spark cluster supports EDP by default
        # because cluster requires a master and slaves >= 1
        wrap_it(data={"cluster_id": uuidutils.generate_uuid(),
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
                                                     "fake", "0.1", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "job_configs": {"configs": {},
                                "params": {},
                                "args": [],
                                "job_execution_info": {}}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "%s job must "
                          "specify edp.java.main_class" % edp.JOB_TYPE_JAVA))

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": ""},
                    "params": {},
                    "args": [],
                    "job_execution_info": {}}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "%s job must "
                          "specify edp.java.main_class" % edp.JOB_TYPE_JAVA))

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": "org.me.myclass"},
                    "params": {},
                    "job_execution_info": {},
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
                                                     "fake", "0.1", [ng])

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "job_configs": {"configs": {},
                                "params": {},
                                "args": [],
                                "job_execution_info": {}}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "%s job must "
                          "specify edp.java.main_class" % edp.JOB_TYPE_SPARK))

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": ""},
                    "params": {},
                    "args": [],
                    "job_execution_info": {}}
            },
            bad_req_i=(1, "INVALID_DATA",
                          "%s job must "
                          "specify edp.java.main_class" % edp.JOB_TYPE_SPARK))

        self._assert_create_object_validation(
            data={
                "cluster_id": uuidutils.generate_uuid(),
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": "org.me.myclass"},
                    "params": {},
                    "job_execution_info": {},
                    "args": []}
            })

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_invalid_start_time_in_job_execution_info(self, now_get):
        configs = {"start": "2015-07-21 14:32:52"}
        now = time.strptime("2015-07-22 14:39:14", "%Y-%m-%d %H:%M:%S")
        now = timeutils.datetime.datetime.fromtimestamp(time.mktime(now))
        now_get.return_value = now

        with testtools.ExpectedException(ex.InvalidJobExecutionInfoException):
            je.check_scheduled_job_execution_info(configs)


class TestJobExecUpdateValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestJobExecUpdateValidation, self).setUp()
        self._create_object_fun = mock.Mock()
        self.scheme = je_schema.JOB_EXEC_UPDATE_SCHEMA

    def test_job_execution_update_types(self):
        data = {
            'is_public': False,
            'is_protected': False,
            'info': {
                'status': 'suspend'
            }
        }
        self._assert_types(data)

    def test_job_execution_update_nothing_required(self):
        self._assert_create_object_validation(
            data={
                'is_public': False,
                'is_protected': False,
                'info': {
                    'status': 'suspend'
                }
            }
        )

    @mock.patch('sahara.conductor.api.LocalApi.job_execution_get')
    def test_je_update_when_protected(self, get_je_p):

        job_exec = mock.Mock(id='123', tenant_id='tenant_1', is_protected=True)
        get_je_p.return_value = job_exec

        # job execution can't be updated if it's marked as protected
        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                je.check_job_execution_update(job_exec, {'job_configs': {}})
            except ex.UpdateFailedException as e:
                self.assert_protected_resource_exception(e)
                raise e
        # job execution can be updated because is_protected flag was
        # set to False
        je.check_job_execution_update(
            job_exec, {'is_protected': False, 'job_configs': {}})

    @mock.patch('sahara.conductor.api.LocalApi.job_execution_get')
    def test_public_je_cancel_delete_from_another_tenant(self, get_je_p):

        job_exec = mock.Mock(id='123', tenant_id='tenant2', is_protected=False,
                             is_public=True)
        get_je_p.return_value = job_exec

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                je.check_job_execution_update(
                    job_exec, data={'is_public': False})
            except ex.UpdateFailedException as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e


class TestJobExecutionCancelDeleteValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestJobExecutionCancelDeleteValidation, self).setUp()
        self.setup_context(tenant_id='tenant1')

    @mock.patch('sahara.conductor.api.LocalApi.job_execution_get')
    def test_je_cancel_delete_when_protected(self, get_je_p):

        job_exec = mock.Mock(id='123', tenant_id='tenant1', is_protected=True)
        get_je_p.return_value = job_exec

        with testtools.ExpectedException(ex.CancelingFailed):
            try:
                je.check_job_execution_cancel(job_exec)
            except ex.CancelingFailed as e:
                self.assert_protected_resource_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                je.check_job_execution_delete(job_exec)
            except ex.DeletionFailed as e:
                self.assert_protected_resource_exception(e)
                raise e

    @mock.patch('sahara.conductor.api.LocalApi.job_execution_get')
    def test_public_je_cancel_delete_from_another_tenant(self, get_je_p):

        job_exec = mock.Mock(id='123', tenant_id='tenant2', is_protected=False,
                             is_public=True)
        get_je_p.return_value = job_exec

        with testtools.ExpectedException(ex.CancelingFailed):
            try:
                je.check_job_execution_cancel(job_exec)
            except ex.CancelingFailed as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                je.check_job_execution_delete(job_exec)
            except ex.DeletionFailed as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e
