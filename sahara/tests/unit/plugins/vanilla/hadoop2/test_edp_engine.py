# Copyright (c) 2017 EasyStack Inc.
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

import mock

from sahara.plugins import exceptions as ex
from sahara.plugins.vanilla.hadoop2 import edp_engine
from sahara.service.edp import job_utils
from sahara.tests.unit import base as sahara_base


class EdpOozieEngineTest(sahara_base.SaharaTestCase):

    engine_path = 'sahara.service.edp.oozie.engine.'

    def setUp(self):
        super(EdpOozieEngineTest, self).setUp()
        self.cluster = mock.Mock()
        job_utils.get_plugin = mock.Mock(return_value='test_plugins')
        self.engine = edp_engine.EdpOozieEngine(self.cluster)

    def test_get_hdfs_user(self):
        self.assertEqual(self.engine.get_hdfs_user(), 'hadoop')

    def test_get_name_node_uri(self):
        cluster = {'info': {
            'HDFS': {
                'NameNode': 'test_url'}}}
        ret = self.engine.get_name_node_uri(cluster)
        self.assertEqual(ret, 'test_url')

    def test_get_oozie_server_uri(self):
        cluster = {'info': {
            'JobFlow': {
                'Oozie': 'test_url'}}}
        ret = self.engine.get_oozie_server_uri(cluster)
        self.assertEqual(ret, 'test_url/oozie/')

    @mock.patch('sahara.plugins.vanilla.utils.get_oozie')
    def test_get_oozie_server(self, get_oozie):
        get_oozie.return_value = 'bingo'
        ret = self.engine.get_oozie_server(self.cluster)
        get_oozie.assert_called_once_with(self.cluster)
        self.assertEqual(ret, 'bingo')

    @mock.patch(engine_path + 'OozieJobEngine.validate_job_execution')
    @mock.patch('sahara.plugins.utils.get_instances_count')
    def test_validate_job_execution(self,
                                    get_instances_count,
                                    validate_job_execution):
        job = mock.Mock()
        data = mock.Mock()
        get_instances_count.return_value = 0
        self.assertRaises(ex.InvalidComponentCountException,
                          self.engine.validate_job_execution,
                          self.cluster, job, data)

        get_instances_count.return_value = 1
        self.engine.validate_job_execution(self.cluster, job, data)
        validate_job_execution.assert_called_once_with(self.cluster,
                                                       job, data)

    @mock.patch('sahara.service.edp.hdfs_helper.create_dir_hadoop2')
    def test_create_hdfs_dir(self, create_dir_hadoop2):
        self.engine.get_hdfs_user = mock.Mock(return_value='test_user')
        remote = mock.Mock()
        dir_name = mock.Mock()
        self.engine.create_hdfs_dir(remote, dir_name)
        create_dir_hadoop2.assert_called_once_with(remote, dir_name,
                                                   'test_user')

    def test_get_resource_manager_uri(self):
        cluster = {'info': {
            'YARN': {
                'ResourceManager': 'test_url'}}}
        ret = self.engine.get_resource_manager_uri(cluster)
        self.assertEqual(ret, 'test_url')
