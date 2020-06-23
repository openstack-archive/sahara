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

from oslo_utils import uuidutils
import testtools

from sahara import conductor as cond
from sahara.service.edp.data_sources import manager as ds_manager
from sahara.service.edp import job_utils
from sahara.tests.unit.service.edp import edp_test_utils as u

conductor = cond.API


class JobUtilsTestCase(testtools.TestCase):

    def setUp(self):
        super(JobUtilsTestCase, self).setUp()
        ds_manager.setup_data_sources()

    def test_args_may_contain_data_sources(self):
        job_configs = None

        # No configs, default false
        by_name, by_uuid = job_utils.may_contain_data_source_refs(job_configs)
        self.assertFalse(by_name | by_uuid)

        # Empty configs, default false
        job_configs = {'configs': {}}
        by_name, by_uuid = job_utils.may_contain_data_source_refs(job_configs)
        self.assertFalse(by_name | by_uuid)

        job_configs['configs'] = {job_utils.DATA_SOURCE_SUBST_NAME: True,
                                  job_utils.DATA_SOURCE_SUBST_UUID: True}
        by_name, by_uuid = job_utils.may_contain_data_source_refs(job_configs)
        self.assertTrue(by_name & by_uuid)

        job_configs['configs'][job_utils.DATA_SOURCE_SUBST_NAME] = False
        by_name, by_uuid = job_utils.may_contain_data_source_refs(job_configs)
        self.assertFalse(by_name)
        self.assertTrue(by_uuid)

        job_configs['configs'][job_utils.DATA_SOURCE_SUBST_UUID] = False
        by_name, by_uuid = job_utils.may_contain_data_source_refs(job_configs)
        self.assertFalse(by_name | by_uuid)

        job_configs['configs'] = {job_utils.DATA_SOURCE_SUBST_NAME: 'True',
                                  job_utils.DATA_SOURCE_SUBST_UUID: 'Fish'}
        by_name, by_uuid = job_utils.may_contain_data_source_refs(job_configs)
        self.assertTrue(by_name)
        self.assertFalse(by_uuid)

    def test_find_possible_data_source_refs_by_name(self):
        id = uuidutils.generate_uuid()
        job_configs = {}
        self.assertEqual([],
                         job_utils.find_possible_data_source_refs_by_name(
                             job_configs))

        name_ref = job_utils.DATA_SOURCE_PREFIX+'name'
        name_ref2 = name_ref+'2'

        job_configs = {'args': ['first', id],
                       'configs': {'config': 'value'},
                       'params': {'param': 'value'}}
        self.assertEqual([],
                         job_utils.find_possible_data_source_refs_by_name(
                             job_configs))

        job_configs = {'args': [name_ref, id],
                       'configs': {'config': 'value'},
                       'params': {'param': 'value'}}
        self.assertEqual(
            ['name'],
            job_utils.find_possible_data_source_refs_by_name(job_configs))

        job_configs = {'args': ['first', id],
                       'configs': {'config': name_ref},
                       'params': {'param': 'value'}}
        self.assertEqual(
            ['name'],
            job_utils.find_possible_data_source_refs_by_name(job_configs))

        job_configs = {'args': ['first', id],
                       'configs': {'config': 'value'},
                       'params': {'param': name_ref}}
        self.assertEqual(
            ['name'],
            job_utils.find_possible_data_source_refs_by_name(job_configs))

        job_configs = {'args': [name_ref, name_ref2, id],
                       'configs': {'config': name_ref},
                       'params': {'param': name_ref}}
        self.assertCountEqual(
            ['name', 'name2'],
            job_utils.find_possible_data_source_refs_by_name(job_configs))

    def test_find_possible_data_source_refs_by_uuid(self):
        job_configs = {}

        name_ref = job_utils.DATA_SOURCE_PREFIX+'name'

        self.assertEqual([],
                         job_utils.find_possible_data_source_refs_by_uuid(
                             job_configs))

        id = uuidutils.generate_uuid()
        job_configs = {'args': ['first', name_ref],
                       'configs': {'config': 'value'},
                       'params': {'param': 'value'}}
        self.assertEqual([],
                         job_utils.find_possible_data_source_refs_by_uuid(
                             job_configs))

        job_configs = {'args': [id, name_ref],
                       'configs': {'config': 'value'},
                       'params': {'param': 'value'}}
        self.assertEqual(
            [id],
            job_utils.find_possible_data_source_refs_by_uuid(job_configs))

        job_configs = {'args': ['first', name_ref],
                       'configs': {'config': id},
                       'params': {'param': 'value'}}
        self.assertEqual(
            [id],
            job_utils.find_possible_data_source_refs_by_uuid(job_configs))

        job_configs = {'args': ['first', name_ref],
                       'configs': {'config': 'value'},
                       'params': {'param': id}}
        self.assertEqual(
            [id],
            job_utils.find_possible_data_source_refs_by_uuid(job_configs))

        id2 = uuidutils.generate_uuid()
        job_configs = {'args': [id, id2, name_ref],
                       'configs': {'config': id},
                       'params': {'param': id}}
        self.assertCountEqual([id, id2],
                              job_utils.find_possible_data_source_refs_by_uuid(
                                  job_configs))

    @mock.patch('sahara.context.ctx')
    @mock.patch('sahara.conductor.API.data_source_get_all')
    def test_resolve_data_source_refs(self, data_source_get_all, ctx):

        ctx.return_value = 'dummy'

        name_ref = job_utils.DATA_SOURCE_PREFIX+'input'
        job_exec_id = uuidutils.generate_uuid()

        input_url = "swift://container/input"
        input = u.create_data_source(input_url,
                                     name="input",
                                     id=uuidutils.generate_uuid())

        output = u.create_data_source("swift://container/output.%JOB_EXEC_ID%",
                                      name="output",
                                      id=uuidutils.generate_uuid())
        output_url = "swift://container/output." + job_exec_id

        by_name = {'input': input,
                   'output': output}

        by_id = {input.id: input,
                 output.id: output}

        # Pretend to be the database
        def _get_all(ctx, **kwargs):
            name = kwargs.get('name')
            if name in by_name:
                name_list = [by_name[name]]
            else:
                name_list = []

            id = kwargs.get('id')
            if id in by_id:
                id_list = [by_id[id]]
            else:
                id_list = []
            return list(set(name_list + id_list))

        data_source_get_all.side_effect = _get_all

        job_configs = {
            'configs': {
                job_utils.DATA_SOURCE_SUBST_NAME: True,
                job_utils.DATA_SOURCE_SUBST_UUID: True},
            'args': [name_ref, output.id, input.id]}
        urls = {}
        ds, nc = job_utils.resolve_data_source_references(job_configs,
                                                          job_exec_id, urls)
        self.assertEqual(2, len(ds))
        self.assertEqual([input.url, output_url, input.url], nc['args'])

        # Substitution not enabled
        job_configs['configs'] = {job_utils.DATA_SOURCE_SUBST_NAME: False,
                                  job_utils.DATA_SOURCE_SUBST_UUID: False}
        ds, nc = job_utils.resolve_data_source_references(job_configs,
                                                          job_exec_id, {})
        self.assertEqual(0, len(ds))
        self.assertEqual(job_configs['args'], nc['args'])
        self.assertEqual(job_configs['configs'], nc['configs'])

        # Substitution enabled but no values to modify
        job_configs['configs'] = {job_utils.DATA_SOURCE_SUBST_NAME: True,
                                  job_utils.DATA_SOURCE_SUBST_UUID: True}
        job_configs['args'] = ['val1', 'val2', 'val3']
        ds, nc = job_utils.resolve_data_source_references(job_configs,
                                                          job_exec_id, {})
        self.assertEqual(0, len(ds))
        self.assertEqual(nc['args'], job_configs['args'])
        self.assertEqual(nc['configs'], job_configs['configs'])

    def test_to_url_dict(self):
        data_source_urls = {'1': ('1_native', '1_runtime'),
                            '2': ('2_native', '2_runtime')}
        self.assertCountEqual({'1': '1_native',
                               '2': '2_native'},
                              job_utils.to_url_dict(data_source_urls))

        self.assertCountEqual({'1': '1_runtime',
                               '2': '2_runtime'},
                              job_utils.to_url_dict(data_source_urls,
                                                    runtime=True))

    @mock.patch('sahara.service.edp.hdfs_helper.configure_cluster_for_hdfs')
    def test_prepare_cluster_for_ds(self, configure):
        data_source_urls = {'1': '1_runtime',
                            '2': '2_runtime'}

        data_source = mock.Mock()
        data_source.type = 'hdfs'
        data_source.id = '1'

        cluster = mock.Mock()
        job_configs = mock.Mock()

        job_utils.prepare_cluster_for_ds([data_source], cluster, job_configs,
                                         data_source_urls)

        configure.assert_called_once()
        configure.assert_called_with(cluster, '1_runtime')
