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

from savanna import context
import savanna.tests.unit.conductor.base as test_base

SAMPLE_DATA_SOURCE = {
    "tenant_id": "test_tenant",
    "name": "ngt_test",
    "description": "test_desc",
    "type": "Cassandra",
    "url": "localhost:1080",
    "credentials": {
        "user": "test",
        "password": "123"
    }
}

SAMPLE_JOB = {
    "tenant_id": "test_tenant",
    "name": "ngt_test",
    "description": "test_desc",
    "type": "db",
    "input_type": "swift",
    "output_type": "swift"
}

SAMPLE_JOB_ORIGIN = {
    "tenant_id": "test_tenant",
    "name": "job_origin_test",
    "description": "test_desc",
    "storage_type": "swift",
    "url": "localhost:1080",
    "credentials": {
        "user": "test",
        "password": "123"
    }
}


SAMPLE_JOB_EXECUTION = {
    "tenant_id": "tenant_id",
    "progress": "0.1",
    "return_code": "1",
    "job_id": "undefined",
    "input_id": "undefined",
    "output_id": "undefined",
    "cluster_id": None
}


class DataSourceTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(DataSourceTest, self).__init__(
            checks=[
                lambda: SAMPLE_DATA_SOURCE
            ], *args, **kwargs)

    def test_crud_operation_create_list_delete(self):
        ctx = context.ctx()
        self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)

        lst = self.api.data_source_get_all(ctx)
        self.assertEqual(len(lst), 1)

        ds_id = lst[0]['id']
        self.api.data_source_destroy(ctx, ds_id)

        lst = self.api.data_source_get_all(ctx)
        self.assertEqual(len(lst), 0)

    def test_duplicate_data_source_create(self):
        ctx = context.ctx()
        self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)
        with self.assertRaises(RuntimeError):
            self.api.data_source_create(ctx, SAMPLE_DATA_SOURCE)

    def test_data_source_fields(self):
        ctx = context.ctx()
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

        with self.assertRaises(RuntimeError):
            self.api.data_source_destroy(ctx, _id)


class JobTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(JobTest, self).__init__(
            checks=[
                lambda: SAMPLE_JOB
            ], *args, **kwargs)

    def test_crud_operation_create_list_delete(self):
        ctx = context.ctx()
        self.api.job_create(ctx, SAMPLE_JOB)

        lst = self.api.job_get_all(ctx)
        self.assertEqual(len(lst), 1)

        job_id = lst[0]['id']
        self.api.job_destroy(ctx, job_id)

        lst = self.api.job_get_all(ctx)
        self.assertEqual(len(lst), 0)

    def test_duplicate_data_source_create(self):
        ctx = context.ctx()
        self.api.job_create(ctx, SAMPLE_JOB)
        with self.assertRaises(RuntimeError):
            self.api.job_create(ctx, SAMPLE_JOB)

    def test_job_fields(self):
        ctx = context.ctx()
        job_db_obj_id = self.api.job_create(ctx, SAMPLE_JOB)['id']

        job_db_obj = self.api.job_get(ctx, job_db_obj_id)
        self.assertIsInstance(job_db_obj, dict)

        for key, val in SAMPLE_JOB.items():
            self.assertEqual(val, job_db_obj.get(key),
                             "Key not found %s" % key)

    def test_job_delete(self):
        ctx = context.ctx()
        job_db_obj = self.api.job_create(ctx, SAMPLE_JOB)
        _id = job_db_obj['id']

        self.api.job_destroy(ctx, _id)

        with self.assertRaises(RuntimeError):
            self.api.job_destroy(ctx, _id)


class JobExecutionTest(test_base.ConductorManagerTestCase):
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
        self.assertEqual(len(lst), 1)

        job_ex_id = lst[0]['id']

        self.assertEqual(lst[0]['progress'], 0.1)
        self.api.job_execution_update(ctx, job_ex_id, {'progress': '0.2'})
        updated_job = self.api.job_execution_get(ctx, job_ex_id)
        self.assertEqual(updated_job['progress'], 0.2)

        self.api.job_execution_destroy(ctx, job_ex_id)

        lst = self.api.job_execution_get_all(ctx)
        self.assertEqual(len(lst), 0)


class JobOriginTest(test_base.ConductorManagerTestCase):
    def __init__(self, *args, **kwargs):
        super(JobOriginTest, self).__init__(
            checks=[
                lambda: SAMPLE_JOB_ORIGIN
            ], *args, **kwargs)

    def test_crud_operation_create_list_delete(self):
        ctx = context.ctx()

        self.api.job_origin_create(ctx, SAMPLE_JOB_ORIGIN)

        lst = self.api.job_origin_get_all(ctx)
        self.assertEqual(len(lst), 1)

        jo = lst[0]['id']
        self.api.job_origin_destroy(ctx, jo)

        lst = self.api.job_origin_get_all(ctx)
        self.assertEqual(len(lst), 0)
