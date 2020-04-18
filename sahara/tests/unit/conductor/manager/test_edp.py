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

import copy
import datetime
from unittest import mock

from sqlalchemy import exc as sa_exc
import testtools

from sahara import context
from sahara.db.sqlalchemy import models as m
from sahara import exceptions as ex
from sahara.service.castellan import config as castellan
import sahara.tests.unit.conductor.base as test_base
from sahara.tests.unit.conductor.manager import test_clusters
from sahara.utils import edp


SAMPLE_DATA_SOURCE = {
    "tenant_id": "tenant_1",
    "name": "ngt_test",
    "description": "test_desc",
    "type": "Cassandra",
    "url": "localhost:1080",
    "credentials": {
        "user": "test",
        "password": "123"
    },
    "is_public": False,
    "is_protected": False
}

SAMPLE_JOB = {
    "tenant_id": "tenant_1",
    "name": "job_test",
    "description": "test_desc",
    "type": edp.JOB_TYPE_PIG,
    "mains": [],
    "is_public": False,
    "is_protected": False
}

SAMPLE_JOB_EXECUTION = {
    "tenant_id": "tenant_1",
    "return_code": "1",
    "job_id": "undefined",
    "input_id": "undefined",
    "output_id": "undefined",
    "start_time": datetime.datetime.now(),
    "cluster_id": None,
    "is_public": False,
    "is_protected": False
}

SAMPLE_CONF_JOB_EXECUTION = {
    "tenant_id": "tenant_1",
    "progress": "0.1",
    "return_code": "1",
    "job_id": "undefined",
    "input_id": "undefined",
    "output_id": "undefined",
    "cluster_id": None,
    "job_configs": {
        "conf2": "value_je",
        "conf3": "value_je"
    }
}

BINARY_DATA = b"vU}\x97\x1c\xdf\xa686\x08\xf2\tf\x0b\xb1}"

SAMPLE_JOB_BINARY_INTERNAL = {
    "tenant_id": "test_tenant",
    "name": "job_test",
    "data": BINARY_DATA,
    "is_public": False,
    "is_protected": False
}


SAMPLE_JOB_BINARY = {
    "tenant_id": "test_tenant",
    "name": "job_binary_test",
    "description": "test_dec",
    "url": "internal-db://test_binary",
    "is_public": False,
    "is_protected": False
}

SAMPLE_JOB_BINARY_UPDATE = {
    "name": "updatedName",
    "url": "internal-db://updated-fake-url"
}

SAMPLE_JOB_BINARY_SWIFT = {
    "tenant_id": "test_tenant",
    "name": "job_binary_test_swift",
    "description": "the description",
    "url": "swift://test_swift_url",
}

SAMPLE_JOB_BINARY_SWIFT_UPDATE = {
    "name": "SwifterName",
    "url": "swift://updated-swift"
}


class DataSourceTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(DataSourceTest, self).__init__(
            checks=[
                lambda: SAMPLE_DATA_SOURCE
            ], *args, **kwargs)

    def setUp(self):
        super(DataSourceTest, self).setUp()
        castellan.validate_config()

    def test_crud_operation_create_list_delete(self):
        ctx = context.ctx()
        self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)

        lst = self.api.data_source_get_all(ctx)
        self.assertEqual(1, len(lst))

        ds_id = lst[0]['id']
        self.api.data_source_destroy(ctx, ds_id)

        lst = self.api.data_source_get_all(ctx)
        self.assertEqual(0, len(lst))

    def test_duplicate_data_source_create(self):
        ctx = context.ctx()
        self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)

    def test_data_source_fields(self):
        ctx = context.ctx()
        ctx.tenant_id = SAMPLE_DATA_SOURCE['tenant_id']
        ds_db_obj_id = self.api.data_source_create(ctx,
                                                   SAMPLE_DATA_SOURCE)['id']

        ds_db_obj = self.api.data_source_get(ctx, ds_db_obj_id)
        self.assertIsInstance(ds_db_obj, dict)

        for key, val in SAMPLE_DATA_SOURCE.items():
            self.assertEqual(val, ds_db_obj.get(key),
                             "Key not found %s" % key)

    def test_data_source_delete(self):
        ctx = context.ctx()
        db_obj_ds = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        _id = db_obj_ds['id']

        self.api.data_source_destroy(ctx, _id)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.data_source_destroy(ctx, _id)

    def test_data_source_search(self):
        ctx = context.ctx()
        ctx.tenant_id = SAMPLE_DATA_SOURCE['tenant_id']
        self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)

        lst = self.api.data_source_get_all(ctx)
        self.assertEqual(1, len(lst))

        kwargs = {'name': SAMPLE_DATA_SOURCE['name'],
                  'tenant_id': SAMPLE_DATA_SOURCE['tenant_id']}
        lst = self.api.data_source_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Valid field but no matching value
        kwargs = {'name': SAMPLE_DATA_SOURCE['name']+"foo"}
        lst = self.api.data_source_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Valid field with substrings
        kwargs = {'name': 'ngt',
                  'tenant_id': SAMPLE_DATA_SOURCE['tenant_id']}
        lst = self.api.data_source_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Invalid field
        self.assertRaises(sa_exc.InvalidRequestError,
                          self.api.data_source_get_all,
                          ctx, **{'badfield': 'somevalue'})

    @mock.patch('sahara.db.sqlalchemy.api.regex_filter')
    def test_data_source_search_regex(self, regex_filter):

        # do this so we can return the correct value
        def _regex_filter(query, cls, regex_cols, search_opts):
            return query, search_opts

        regex_filter.side_effect = _regex_filter

        ctx = context.ctx()
        self.api.data_source_get_all(ctx)
        self.assertEqual(0, regex_filter.call_count)

        self.api.data_source_get_all(ctx, regex_search=True, name="fox")
        self.assertEqual(1, regex_filter.call_count)
        args, kwargs = regex_filter.call_args
        self.assertIs(args[1], m.DataSource)
        self.assertEqual(args[2], ["name", "description", "url"])
        self.assertEqual(args[3], {"name": "fox"})

    def test_data_source_count_in(self):
        ctx = context.ctx()
        ctx.tenant_id = SAMPLE_DATA_SOURCE['tenant_id']
        src = copy.copy(SAMPLE_DATA_SOURCE)
        self.api.data_source_create(ctx, src)

        cnt = self.api.data_source_count(ctx, name='ngt_test')
        self.assertEqual(1, cnt)

        cnt = self.api.data_source_count(ctx, name=('ngt_test',
                                                    'test2', 'test3'))
        self.assertEqual(1, cnt)

        cnt = self.api.data_source_count(ctx, name=('test1',
                                                    'test2', 'test3'))
        self.assertEqual(0, cnt)

        lst = self.api.data_source_get_all(ctx, name='ngt_test')
        myid = lst[0]['id']
        cnt = self.api.data_source_count(ctx,
                                         name=('ngt_test', 'test2', 'test3'),
                                         id=myid)
        self.assertEqual(1, cnt)

        cnt = self.api.data_source_count(ctx,
                                         name=('ngt_test', 'test2', 'test3'),
                                         id=(myid, '2'))
        self.assertEqual(1, cnt)

    def test_data_source_count_like(self):
        ctx = context.ctx()
        ctx.tenant_id = SAMPLE_DATA_SOURCE['tenant_id']
        src = copy.copy(SAMPLE_DATA_SOURCE)
        self.api.data_source_create(ctx, src)

        cnt = self.api.data_source_count(ctx, name='ngt_test')
        self.assertEqual(1, cnt)

        cnt = self.api.data_source_count(ctx, name='ngt%')
        self.assertEqual(1, cnt)

        cnt = self.api.data_source_count(ctx,
                                         name=('ngt_test',),
                                         url='localhost%')
        self.assertEqual(1, cnt)

        cnt = self.api.data_source_count(ctx,
                                         name=('ngt_test',),
                                         url='localhost')
        self.assertEqual(0, cnt)

    def test_data_source_update(self):
        ctx = context.ctx()
        orig = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        update_json = {"name": "updatedName",
                       "url": "swift://updatedFakeUrl"}
        updated = self.api.data_source_update(ctx, orig["id"], update_json)
        self.assertEqual("updatedName", updated["name"])
        self.assertEqual("swift://updatedFakeUrl", updated["url"])

    def test_ds_update_delete_when_protected(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_DATA_SOURCE)
        sample['is_protected'] = True
        ds = self.api.data_source_create(ctx, sample)
        ds_id = ds["id"]

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.data_source_update(ctx, ds_id, {"name": "ds"})
            except ex.UpdateFailedException as e:
                self.assert_protected_resource_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.data_source_destroy(ctx, ds_id)
            except ex.DeletionFailed as e:
                self.assert_protected_resource_exception(e)
                raise e

        self.api.data_source_update(ctx, ds_id,
                                    {"name": "ds", "is_protected": False})

    def test_public_ds_update_delete_from_another_tenant(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_DATA_SOURCE)
        sample['is_public'] = True
        ds = self.api.data_source_create(ctx, sample)
        ds_id = ds["id"]
        ctx.tenant_id = 'tenant_2'

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.data_source_update(ctx, ds_id, {"name": "ds"})
            except ex.UpdateFailedException as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.data_source_destroy(ctx, ds_id)
            except ex.DeletionFailed as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e


class JobExecutionTest(test_base.ConductorManagerTestCase):
    def setUp(self):
        super(JobExecutionTest, self).setUp()
        castellan.validate_config()

    def test_crud_operation_create_list_delete_update(self):
        ctx = context.ctx()
        job = self.api.job_create(ctx, SAMPLE_JOB)
        ds_input = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT = copy.copy(SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT['name'] = 'output'
        ds_output = self.api.data_source_create(ctx, SAMPLE_DATA_OUTPUT)

        SAMPLE_JOB_EXECUTION['job_id'] = job['id']
        SAMPLE_JOB_EXECUTION['input_id'] = ds_input['id']
        SAMPLE_JOB_EXECUTION['output_id'] = ds_output['id']

        self.api.job_execution_create(ctx, SAMPLE_JOB_EXECUTION)

        lst = self.api.job_execution_get_all(ctx)
        self.assertEqual(1, len(lst))

        count = self.api.job_execution_count(ctx)
        self.assertEqual(1, count)

        job_ex_id = lst[0]['id']

        self.assertIsNone(lst[0]['info'])
        new_info = {"status": edp.JOB_STATUS_PENDING}
        self.api.job_execution_update(ctx, job_ex_id, {'info': new_info})
        updated_job = self.api.job_execution_get(ctx, job_ex_id)
        self.assertEqual(new_info, updated_job['info'])
        self.assertEqual(SAMPLE_JOB_EXECUTION['start_time'],
                         updated_job['start_time'])

        self.api.job_execution_destroy(ctx, job_ex_id)

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.job_execution_update(ctx, job_ex_id, {'info': new_info})

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.job_execution_destroy(ctx, job_ex_id)

        lst = self.api.job_execution_get_all(ctx)
        self.assertEqual(0, len(lst))

    def test_crud_operation_on_configured_jobs(self):
        ctx = context.ctx()
        job = self.api.job_create(ctx, SAMPLE_JOB)
        ds_input = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT = copy.copy(SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT['name'] = 'output'
        ds_output = self.api.data_source_create(ctx, SAMPLE_DATA_OUTPUT)

        SAMPLE_CONF_JOB_EXECUTION['job_id'] = job['id']
        SAMPLE_CONF_JOB_EXECUTION['input_id'] = ds_input['id']
        SAMPLE_CONF_JOB_EXECUTION['output_id'] = ds_output['id']

        self.api.job_execution_create(ctx, SAMPLE_CONF_JOB_EXECUTION)

        lst = self.api.job_execution_get_all(ctx)
        self.assertEqual(1, len(lst))

        job_ex = lst[0]
        configs = {
            'conf2': 'value_je',
            'conf3': 'value_je'
        }
        self.assertEqual(configs, job_ex['job_configs'])

    def test_null_data_sources(self):
        ctx = context.ctx()
        job = self.api.job_create(ctx, SAMPLE_JOB)

        SAMPLE_CONF_JOB_EXECUTION['job_id'] = job['id']
        SAMPLE_CONF_JOB_EXECUTION['input_id'] = None
        SAMPLE_CONF_JOB_EXECUTION['output_id'] = None

        id = self.api.job_execution_create(ctx,
                                           SAMPLE_CONF_JOB_EXECUTION)['id']
        job_exec = self.api.job_execution_get(ctx, id)

        self.assertIsNone(job_exec['input_id'])
        self.assertIsNone(job_exec['output_id'])

    def test_deletion_constraints_on_data_and_jobs(self):
        ctx = context.ctx()
        job = self.api.job_create(ctx, SAMPLE_JOB)
        ds_input = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT = copy.copy(SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT['name'] = 'output'
        ds_output = self.api.data_source_create(ctx, SAMPLE_DATA_OUTPUT)

        SAMPLE_CONF_JOB_EXECUTION['job_id'] = job['id']
        SAMPLE_CONF_JOB_EXECUTION['input_id'] = ds_input['id']
        SAMPLE_CONF_JOB_EXECUTION['output_id'] = ds_output['id']

        self.api.job_execution_create(ctx, SAMPLE_CONF_JOB_EXECUTION)

        with testtools.ExpectedException(ex.DeletionFailed):
            self.api.data_source_destroy(ctx, ds_input['id'])
        with testtools.ExpectedException(ex.DeletionFailed):
            self.api.data_source_destroy(ctx, ds_output['id'])
        with testtools.ExpectedException(ex.DeletionFailed):
            self.api.job_destroy(ctx, job['id'])

    def test_job_execution_search(self):
        ctx = context.ctx()
        jvals = copy.copy(SAMPLE_JOB)
        jvals["name"] = "frederica"
        job = self.api.job_create(ctx, jvals)

        ds_input = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT = copy.copy(SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT['name'] = 'output'
        ds_output = self.api.data_source_create(ctx, SAMPLE_DATA_OUTPUT)

        job_exec = copy.copy(SAMPLE_JOB_EXECUTION)

        job_exec['job_id'] = job['id']
        job_exec['input_id'] = ds_input['id']
        job_exec['output_id'] = ds_output['id']

        ctx.tenant_id = job_exec['tenant_id']
        self.api.job_execution_create(ctx, job_exec)

        lst = self.api.job_execution_get_all(ctx)
        self.assertEqual(1, len(lst))

        kwargs = {'tenant_id': job_exec['tenant_id']}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Valid field but no matching value
        kwargs = {'job_id': job_exec['job_id']+"foo"}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Valid field with substrings
        kwargs = {'job.name': "red"}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Invalid field
        self.assertRaises(sa_exc.InvalidRequestError,
                          self.api.job_execution_get_all,
                          ctx, **{'badfield': 'somevalue'})

    @mock.patch('sahara.db.sqlalchemy.api.regex_filter')
    def test_job_execution_search_regex(self, regex_filter):

        # do this so we can return the correct value
        def _regex_filter(query, cls, regex_cols, search_opts):
            return query, search_opts

        regex_filter.side_effect = _regex_filter

        ctx = context.ctx()
        self.api.job_execution_get_all(ctx)
        self.assertEqual(0, regex_filter.call_count)

        self.api.job_execution_get_all(ctx, regex_search=True,
                                       **{"job.name": "fox",
                                          "cluster.name": "jack",
                                          "id": "124"})

        self.assertEqual(3, regex_filter.call_count)

        # First call, after externals were removed
        args, kwargs = regex_filter.call_args_list[0]
        self.assertIs(args[1], m.JobExecution)
        self.assertEqual(args[2], ["job.name", "cluster.name"])
        self.assertEqual(args[3], {"id": "124"})

        # Second call, looking for cluster.name
        args, kwargs = regex_filter.call_args_list[1]
        self.assertIs(args[1], m.Cluster)
        self.assertEqual(args[2], ["name"])
        self.assertEqual(args[3], {"name": "jack"})

        # Third call, looking for job.name
        args, kwargs = regex_filter.call_args_list[2]
        self.assertIs(args[1], m.Job)
        self.assertEqual(args[2], ["name"])
        self.assertEqual(args[3], {"name": "fox"})

    def test_job_execution_advanced_search(self):
        ctx = context.ctx()
        job = self.api.job_create(ctx, SAMPLE_JOB)
        ds_input = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT = copy.copy(SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT['name'] = 'output'
        ds_output = self.api.data_source_create(ctx, SAMPLE_DATA_OUTPUT)

        # Create a cluster
        cl1 = self.api.cluster_create(ctx, test_clusters.SAMPLE_CLUSTER)

        # Create a second cluster with a different name
        cl2_vals = copy.copy(test_clusters.SAMPLE_CLUSTER)
        cl2_vals['name'] = 'test_cluster2'
        cl2 = self.api.cluster_create(ctx, cl2_vals)

        my_sample_job_exec = copy.copy(SAMPLE_JOB_EXECUTION)

        my_sample_job_exec['job_id'] = job['id']
        my_sample_job_exec['input_id'] = ds_input['id']
        my_sample_job_exec['output_id'] = ds_output['id']
        my_sample_job_exec['cluster_id'] = cl1['id']

        # Run job on cluster 1
        self.api.job_execution_create(ctx, my_sample_job_exec)

        # Run the same job on cluster 2 and set status
        my_sample_job_exec['cluster_id'] = cl2['id']
        my_sample_job_exec['info'] = {'status': 'KiLLeD'}
        self.api.job_execution_create(ctx, my_sample_job_exec)

        # Search only with job execution fields (finds both)
        lst = self.api.job_execution_get_all(ctx, **{'return_code': 1})
        self.assertEqual(2, len(lst))

        # Search on cluster name
        kwargs = {'cluster.name': cl1['name'],
                  'return_code': 1}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Search on cluster name and job name
        kwargs = {'cluster.name': cl1['name'],
                  'job.name': SAMPLE_JOB['name'],
                  'return_code': 1}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Search on cluster name, job name, and status
        kwargs = {'cluster.name': cl2['name'],
                  'job.name': SAMPLE_JOB['name'],
                  'status': 'killed',
                  'return_code': 1}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Search on job name (finds both)
        kwargs = {'job.name': SAMPLE_JOB['name'],
                  'return_code': 1}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(2, len(lst))

        # invalid cluster name value
        kwargs = {'cluster.name': cl1['name']+'foo',
                  'job.name': SAMPLE_JOB['name']}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # invalid job name value
        kwargs = {'cluster.name': cl1['name'],
                  'job.name': SAMPLE_JOB['name']+'foo'}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # invalid status value
        kwargs = {'cluster.name': cl1['name'],
                  'status': 'PENDING'}
        lst = self.api.job_execution_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))


class JobTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(JobTest, self).__init__(
            checks=[
                lambda: SAMPLE_JOB
            ], *args, **kwargs)

    def test_crud_operation_create_list_delete_update(self):
        ctx = context.ctx()

        self.api.job_create(ctx, SAMPLE_JOB)

        lst = self.api.job_get_all(ctx)
        self.assertEqual(1, len(lst))

        jo_id = lst[0]['id']

        update_jo = self.api.job_update(ctx, jo_id,
                                        {'description': 'update'})
        self.assertEqual('update', update_jo['description'])

        self.api.job_destroy(ctx, jo_id)

        lst = self.api.job_get_all(ctx)
        self.assertEqual(0, len(lst))

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.job_destroy(ctx, jo_id)

    def test_job_fields(self):
        ctx = context.ctx()
        ctx.tenant_id = SAMPLE_JOB['tenant_id']
        job_id = self.api.job_create(ctx, SAMPLE_JOB)['id']

        job = self.api.job_get(ctx, job_id)
        self.assertIsInstance(job, dict)

        for key, val in SAMPLE_JOB.items():
            self.assertEqual(val, job.get(key),
                             "Key not found %s" % key)

    def test_job_search(self):
        ctx = context.ctx()
        job = copy.copy(SAMPLE_JOB)
        job["name"] = "frederica"
        job["description"] = "thebestjob"
        ctx.tenant_id = job['tenant_id']
        self.api.job_create(ctx, job)

        lst = self.api.job_get_all(ctx)
        self.assertEqual(1, len(lst))

        kwargs = {'name': job['name'],
                  'tenant_id': job['tenant_id']}
        lst = self.api.job_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Valid field but no matching value
        lst = self.api.job_get_all(ctx, **{'name': job['name']+"foo"})
        self.assertEqual(0, len(lst))

        # Valid field with substrings
        kwargs = {'name': "red",
                  'description': "best"}
        lst = self.api.job_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Invalid field
        self.assertRaises(sa_exc.InvalidRequestError,
                          self.api.job_get_all,
                          ctx, **{'badfield': 'somevalue'})

    @mock.patch('sahara.db.sqlalchemy.api.regex_filter')
    def test_job_search_regex(self, regex_filter):

        # do this so we can return the correct value
        def _regex_filter(query, cls, regex_cols, search_opts):
            return query, search_opts

        regex_filter.side_effect = _regex_filter

        ctx = context.ctx()
        self.api.job_get_all(ctx)
        self.assertEqual(0, regex_filter.call_count)

        self.api.job_get_all(ctx, regex_search=True, name="fox")
        self.assertEqual(1, regex_filter.call_count)
        args, kwargs = regex_filter.call_args
        self.assertIs(args[1], m.Job)
        self.assertEqual(args[2], ["name", "description"])
        self.assertEqual(args[3], {"name": "fox"})

    def test_job_update_delete_when_protected(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_JOB)
        sample['is_protected'] = True
        job = self.api.job_create(ctx, sample)
        job_id = job["id"]

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.job_update(ctx, job_id, {"name": "job"})
            except ex.UpdateFailedException as e:
                self.assert_protected_resource_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.job_destroy(ctx, job_id)
            except ex.DeletionFailed as e:
                self.assert_protected_resource_exception(e)
                raise e

        self.api.job_update(ctx, job_id, {"name": "job",
                                          "is_protected": False})

    def test_public_job_update_delete_from_another_tenant(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_JOB)
        sample['is_public'] = True
        job = self.api.job_create(ctx, sample)
        job_id = job["id"]
        ctx.tenant_id = 'tenant_2'

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.job_update(ctx, job_id, {"name": "job"})
            except ex.UpdateFailedException as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.job_destroy(ctx, job_id)
            except ex.DeletionFailed as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e


class JobBinaryInternalTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(JobBinaryInternalTest, self).__init__(
            checks=[
                lambda: SAMPLE_JOB_BINARY_INTERNAL
            ], *args, **kwargs)

    def test_crud_operation_create_list_delete_update(self):
        ctx = context.ctx()

        self.api.job_binary_internal_create(ctx, SAMPLE_JOB_BINARY_INTERNAL)

        lst = self.api.job_binary_internal_get_all(ctx)
        self.assertEqual(1, len(lst))

        job_bin_int_id = lst[0]['id']

        update_jbi = self.api.job_binary_internal_update(
            ctx, job_bin_int_id, {'name': 'newname'})

        self.assertEqual('newname', update_jbi['name'])

        self.api.job_binary_internal_destroy(ctx, job_bin_int_id)

        lst = self.api.job_binary_internal_get_all(ctx)
        self.assertEqual(0, len(lst))

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.job_binary_internal_destroy(ctx, job_bin_int_id)

    def test_duplicate_job_binary_internal_create(self):
        ctx = context.ctx()
        self.api.job_binary_internal_create(ctx, SAMPLE_JOB_BINARY_INTERNAL)
        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.job_binary_internal_create(ctx,
                                                SAMPLE_JOB_BINARY_INTERNAL)

    def test_job_binary_internal_get_raw(self):
        ctx = context.ctx()

        id = self.api.job_binary_internal_create(ctx,
                                                 SAMPLE_JOB_BINARY_INTERNAL
                                                 )['id']
        data = self.api.job_binary_internal_get_raw_data(ctx, id)
        self.assertEqual(SAMPLE_JOB_BINARY_INTERNAL["data"], data)

        self.api.job_binary_internal_destroy(ctx, id)

        data = self.api.job_binary_internal_get_raw_data(ctx, id)
        self.assertIsNone(data)

    def test_job_binary_internal_fields(self):
        ctx = context.ctx()
        ctx.tenant_id = SAMPLE_JOB_BINARY_INTERNAL['tenant_id']
        id = self.api.job_binary_internal_create(
            ctx, SAMPLE_JOB_BINARY_INTERNAL)['id']

        internal = self.api.job_binary_internal_get(ctx, id)
        self.assertIsInstance(internal, dict)
        with testtools.ExpectedException(KeyError):
            internal["data"]

        internal["data"] = self.api.job_binary_internal_get_raw_data(ctx, id)
        for key, val in SAMPLE_JOB_BINARY_INTERNAL.items():
            if key == "datasize":
                self.assertEqual(len(BINARY_DATA), internal["datasize"])
            else:
                self.assertEqual(val, internal.get(key),
                                 "Key not found %s" % key)

    def test_job_binary_internal_search(self):
        ctx = context.ctx()
        jbi = copy.copy(SAMPLE_JOB_BINARY_INTERNAL)
        jbi["name"] = "frederica"
        ctx.tenant_id = jbi['tenant_id']
        self.api.job_binary_internal_create(ctx, jbi)

        lst = self.api.job_binary_internal_get_all(ctx)
        self.assertEqual(1, len(lst))

        kwargs = {'name': jbi['name'],
                  'tenant_id': jbi['tenant_id']}
        lst = self.api.job_binary_internal_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Valid field but no matching value
        kwargs = {'name': jbi['name']+"foo"}
        lst = self.api.job_binary_internal_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Valid field with substrings
        kwargs = {'name': "red"}
        lst = self.api.job_binary_internal_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Invalid field
        self.assertRaises(sa_exc.InvalidRequestError,
                          self.api.job_binary_internal_get_all,
                          ctx, **{'badfield': 'junk'})

    @mock.patch('sahara.db.sqlalchemy.api.regex_filter')
    def test_job_binary_internal_search_regex(self, regex_filter):

        # do this so we can return the correct value
        def _regex_filter(query, cls, regex_cols, search_opts):
            return query, search_opts

        regex_filter.side_effect = _regex_filter

        ctx = context.ctx()
        self.api.job_binary_internal_get_all(ctx)
        self.assertEqual(0, regex_filter.call_count)

        self.api.job_binary_internal_get_all(ctx,
                                             regex_search=True, name="fox")
        self.assertEqual(1, regex_filter.call_count)
        args, kwargs = regex_filter.call_args
        self.assertIs(args[1], m.JobBinaryInternal)
        self.assertEqual(args[2], ["name"])
        self.assertEqual(args[3], {"name": "fox"})

    def test_jbi_update_delete_when_protected(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_JOB_BINARY_INTERNAL)
        sample['is_protected'] = True
        jbi = self.api.job_binary_internal_create(ctx, sample)
        jbi_id = jbi["id"]

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.job_binary_internal_update(ctx, jbi_id,
                                                    {"name": "jbi"})
            except ex.UpdateFailedException as e:
                self.assert_protected_resource_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.job_binary_internal_destroy(ctx, jbi_id)
            except ex.DeletionFailed as e:
                self.assert_protected_resource_exception(e)
                raise e

        self.api.job_binary_internal_update(ctx, jbi_id,
                                            {"name": "jbi",
                                             "is_protected": False})

    def test_public_jbi_update_delete_from_another_tenant(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_JOB_BINARY_INTERNAL)
        sample['is_public'] = True
        jbi = self.api.job_binary_internal_create(ctx, sample)
        jbi_id = jbi["id"]
        ctx.tenant_id = 'tenant_2'

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.job_binary_internal_update(ctx, jbi_id,
                                                    {"name": "jbi"})
            except ex.UpdateFailedException as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.job_binary_internal_destroy(ctx, jbi_id)
            except ex.DeletionFailed as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e


class JobBinaryTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(JobBinaryTest, self).__init__(
            checks=[
                lambda: SAMPLE_JOB_BINARY
            ], *args, **kwargs)

    def setUp(self):
        super(JobBinaryTest, self).setUp()
        castellan.validate_config()

    def test_crud_operation_create_list_delete(self):
        ctx = context.ctx()

        self.api.job_binary_create(ctx, SAMPLE_JOB_BINARY)

        lst = self.api.job_binary_get_all(ctx)
        self.assertEqual(1, len(lst))

        job_binary_id = lst[0]['id']
        self.api.job_binary_destroy(ctx, job_binary_id)

        lst = self.api.job_binary_get_all(ctx)
        self.assertEqual(0, len(lst))

        with testtools.ExpectedException(ex.NotFoundException):
            self.api.job_binary_destroy(ctx, job_binary_id)

    def test_job_binary_fields(self):
        ctx = context.ctx()
        ctx.tenant_id = SAMPLE_JOB_BINARY['tenant_id']
        job_binary_id = self.api.job_binary_create(ctx,
                                                   SAMPLE_JOB_BINARY)['id']

        job_binary = self.api.job_binary_get(ctx, job_binary_id)
        self.assertIsInstance(job_binary, dict)

        for key, val in SAMPLE_JOB_BINARY.items():
            self.assertEqual(val, job_binary.get(key),
                             "Key not found %s" % key)

    def _test_job_binary_referenced(self, reference):
        ctx = context.ctx()
        job_binary_id = self.api.job_binary_create(ctx,
                                                   SAMPLE_JOB_BINARY)['id']

        job_values = copy.copy(SAMPLE_JOB)
        job_values[reference] = [job_binary_id]
        job_id = self.api.job_create(ctx, job_values)['id']

        # Delete while referenced, fails
        with testtools.ExpectedException(ex.DeletionFailed):
            self.api.job_binary_destroy(ctx, job_binary_id)

        # Delete while not referenced
        self.api.job_destroy(ctx, job_id)
        self.api.job_binary_destroy(ctx, job_binary_id)
        lst = self.api.job_binary_get_all(ctx)
        self.assertEqual(0, len(lst))

    def test_job_binary_referenced_mains(self):
        self._test_job_binary_referenced("mains")

    def test_job_binary_referenced_libs(self):
        self._test_job_binary_referenced("libs")

    def test_duplicate_job_binary_create(self):
        ctx = context.ctx()
        self.api.job_binary_create(ctx, SAMPLE_JOB_BINARY)
        with testtools.ExpectedException(ex.DBDuplicateEntry):
            self.api.job_binary_create(ctx,
                                       SAMPLE_JOB_BINARY)

    def test_job_binary_search(self):
        ctx = context.ctx()
        jb = copy.copy(SAMPLE_JOB_BINARY)
        jb["name"] = "frederica"
        jb["url"] = "http://thebestbinary"
        ctx.tenant_id = jb['tenant_id']
        self.api.job_binary_create(ctx, jb)

        lst = self.api.job_binary_get_all(ctx)
        self.assertEqual(1, len(lst))

        kwargs = {'name': jb['name'],
                  'tenant_id': jb['tenant_id']}
        lst = self.api.job_binary_get_all(ctx, **kwargs)
        self.assertEqual(1, len(lst))

        # Valid field but no matching value
        kwargs = {'name': jb['name']+"foo"}
        lst = self.api.job_binary_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Valid field with substrings
        kwargs = {'name': "red",
                  'url': "best"}
        lst = self.api.job_binary_get_all(ctx, **kwargs)
        self.assertEqual(0, len(lst))

        # Invalid field
        self.assertRaises(sa_exc.InvalidRequestError,
                          self.api.job_binary_get_all,
                          ctx, **{'badfield': 'somevalue'})

    @mock.patch('sahara.db.sqlalchemy.api.regex_filter')
    def test_job_binary_search_regex(self, regex_filter):

        # do this so we can return the correct value
        def _regex_filter(query, cls, regex_cols, search_opts):
            return query, search_opts

        regex_filter.side_effect = _regex_filter

        ctx = context.ctx()
        self.api.job_binary_get_all(ctx)
        self.assertEqual(0, regex_filter.call_count)

        self.api.job_binary_get_all(ctx, regex_search=True, name="fox")
        self.assertEqual(1, regex_filter.call_count)
        args, kwargs = regex_filter.call_args
        self.assertIs(args[1], m.JobBinary)
        self.assertEqual(args[2], ["name", "description", "url"])
        self.assertEqual(args[3], {"name": "fox"})

    def test_job_binary_update(self):
        ctx = context.ctx()

        original = self.api.job_binary_create(ctx, SAMPLE_JOB_BINARY_SWIFT)
        updated = self.api.job_binary_update(
            ctx, original["id"], SAMPLE_JOB_BINARY_SWIFT_UPDATE)
        # Make sure that the update did indeed succeed
        self.assertEqual(
            SAMPLE_JOB_BINARY_SWIFT_UPDATE["name"], updated["name"])
        self.assertEqual(SAMPLE_JOB_BINARY_SWIFT_UPDATE["url"], updated["url"])

        # Make sure we do NOT update a binary in use by a PENDING job
        self._create_job_execution_ref_job_binary(ctx, original["id"])
        with testtools.ExpectedException(ex.UpdateFailedException):
            self.api.job_binary_update(
                ctx, original["id"], SAMPLE_JOB_BINARY_SWIFT_UPDATE)

        original = self.api.job_binary_create(ctx, SAMPLE_JOB_BINARY)
        # Make sure that internal URL update fails
        with testtools.ExpectedException(ex.UpdateFailedException):
            self.api.job_binary_update(
                ctx, original["id"], SAMPLE_JOB_BINARY_UPDATE)

    def _create_job_execution_ref_job_binary(self, ctx, jb_id):
        JOB_REF_BINARY = copy.copy(SAMPLE_JOB)
        JOB_REF_BINARY["mains"] = [jb_id]
        job = self.api.job_create(ctx, JOB_REF_BINARY)
        ds_input = self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT = copy.copy(SAMPLE_DATA_SOURCE)
        SAMPLE_DATA_OUTPUT['name'] = 'output'
        ds_output = self.api.data_source_create(ctx, SAMPLE_DATA_OUTPUT)
        SAMPLE_JOB_EXECUTION['job_id'] = job['id']
        SAMPLE_JOB_EXECUTION['input_id'] = ds_input['id']
        SAMPLE_JOB_EXECUTION['output_id'] = ds_output['id']

        self.api.job_execution_create(ctx, SAMPLE_JOB_EXECUTION)
        lst = self.api.job_execution_get_all(ctx)
        job_ex_id = lst[0]["id"]
        new_info = {"status": edp.JOB_STATUS_PENDING}
        self.api.job_execution_update(ctx, job_ex_id, {"info": new_info})

    def test_jb_update_delete_when_protected(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_JOB_BINARY)
        sample['is_protected'] = True
        jb = self.api.job_binary_create(ctx, sample)
        jb_id = jb["id"]

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.job_binary_update(ctx, jb_id, {"name": "jb"})
            except ex.UpdateFailedException as e:
                self.assert_protected_resource_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.job_binary_destroy(ctx, jb_id)
            except ex.DeletionFailed as e:
                self.assert_protected_resource_exception(e)
                raise e

        self.api.job_binary_update(ctx, jb_id, {"name": "jb",
                                                "is_protected": False})

    def test_public_jb_update_delete_from_another_tenant(self):
        ctx = context.ctx()
        sample = copy.deepcopy(SAMPLE_JOB_BINARY)
        sample['is_public'] = True
        jb = self.api.job_binary_create(ctx, sample)
        jb_id = jb["id"]
        ctx.tenant_id = 'tenant_2'

        with testtools.ExpectedException(ex.UpdateFailedException):
            try:
                self.api.job_binary_update(ctx, jb_id, {"name": "jb"})
            except ex.UpdateFailedException as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e

        with testtools.ExpectedException(ex.DeletionFailed):
            try:
                self.api.job_binary_destroy(ctx, jb_id)
            except ex.DeletionFailed as e:
                self.assert_created_in_another_tenant_exception(e)
                raise e
