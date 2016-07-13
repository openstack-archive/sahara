# Copyright (c) 2014 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.lib.common.utils import data_utils

from sahara.tests.tempest.scenario.data_processing.client_tests import base


class DataSourceTest(base.BaseDataProcessingTest):
    def _check_data_source_create(self, source_body):
        source_name = data_utils.rand_name('sahara-data-source')
        # create data source
        resp_body = self.create_data_source(source_name, **source_body)
        # check that source created successfully
        self.assertEqual(source_name, resp_body.name)
        if source_body['type'] == 'swift':
            source_body = self.swift_data_source
        self.assertDictContainsSubset(source_body, resp_body.__dict__)

        return resp_body.id, source_name

    def _check_data_source_list(self, source_id, source_name):
        # check for data source in list
        source_list = self.client.data_sources.list()
        sources_info = [(source.id, source.name) for source in source_list]
        self.assertIn((source_id, source_name), sources_info)

    def _check_data_source_get(self, source_id, source_name, source_body):
        # check data source fetch by id
        source = self.client.data_sources.get(source_id)
        self.assertEqual(source_name, source.name)
        self.assertDictContainsSubset(source_body, source.__dict__)

    def _check_data_source_update(self, source_id):
        values = {
            'name': data_utils.rand_name('updated-sahara-data-source'),
            'description': 'description',
            'type': 'hdfs',
            'url': 'hdfs://user/foo'
        }

        source = self.client.data_sources.update(source_id, values)

        self.assertDictContainsSubset(values, source.data_source)

    def _check_data_source_delete(self, source_id):
        # delete data source
        self.client.data_sources.delete(source_id)
        # check that data source really deleted
        source_list = self.client.data_sources.list()
        self.assertNotIn(source_id, [source.id for source in source_list])

    def test_swift_data_source(self):
        # Create extra self.swift_data_source variable to use for comparison to
        # data source response body because response body has no 'credentials'
        # field.
        self.swift_data_source = self.swift_data_source_with_creds.copy()
        del self.swift_data_source['credentials']
        source_id, source_name = self._check_data_source_create(
            self.swift_data_source_with_creds)
        self._check_data_source_list(source_id, source_name)
        self._check_data_source_get(source_id, source_name,
                                    self.swift_data_source)
        self._check_data_source_delete(source_id)

    def test_local_hdfs_data_source(self):
        source_id, source_name = self._check_data_source_create(
            self.local_hdfs_data_source)
        self._check_data_source_list(source_id, source_name)
        self._check_data_source_get(source_id, source_name,
                                    self.local_hdfs_data_source)
        self._check_data_source_delete(source_id)

    def test_external_hdfs_data_source(self):
        source_id, source_name = self._check_data_source_create(
            self.external_hdfs_data_source)
        self._check_data_source_list(source_id, source_name)
        self._check_data_source_get(source_id, source_name,
                                    self.external_hdfs_data_source)
        self._check_data_source_update(source_id)
        self._check_data_source_delete(source_id)
