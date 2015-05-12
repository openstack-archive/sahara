# Copyright (c) 2014 OpenStack Foundation
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

from sahara.plugins import base as pb
from sahara.service.edp.oozie import engine as oe
from sahara.tests.unit import base
from sahara.tests.unit.service.edp import edp_test_utils as u
from sahara.utils import edp


class TestOozieEngine(base.SaharaTestCase):
    def setUp(self):
        super(TestOozieEngine, self).setUp()
        pb.setup_plugins()

    def test_add_postfix(self):
        oje = FakeOozieJobEngine(u.create_cluster())

        self.override_config("job_workflow_postfix", 'caba')
        res = oje._add_postfix('aba')
        self.assertEqual("aba/caba/", res)

        self.override_config("job_workflow_postfix", '')
        res = oje._add_postfix('aba')
        self.assertEqual("aba/", res)

    def test_get_oozie_job_params(self):
        oje = FakeOozieJobEngine(u.create_cluster())
        oozie_params = {'oozie.libpath': '/mylibpath',
                        'oozie.wf.application.path': '/wrong'}
        scheduled_params = {'start': '2015-06-10T06:05Z',
                            'end': '2015-06-10T06:50Z',
                            'frequency': '10'}
        job_dir = '/job_dir'
        job_execution_type = 'workflow'
        job_params = oje._get_oozie_job_params('hadoop',
                                               '/tmp', oozie_params, True,
                                               scheduled_params, job_dir,
                                               job_execution_type)
        self.assertEqual('http://localhost:50030', job_params["jobTracker"])
        self.assertEqual('hdfs://localhost:8020', job_params["nameNode"])
        self.assertEqual('hadoop', job_params["user.name"])
        self.assertEqual('hdfs://localhost:8020/tmp',
                         job_params['oozie.wf.application.path'])
        self.assertEqual("/mylibpath,hdfs://localhost:8020/user/"
                         "sahara-hbase-lib", job_params['oozie.libpath'])

        # Make sure this doesn't raise an exception
        job_params = oje._get_oozie_job_params('hadoop',
                                               '/tmp', {}, True)
        self.assertEqual("hdfs://localhost:8020/user/"
                         "sahara-hbase-lib", job_params['oozie.libpath'])

    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper')
    @mock.patch('sahara.conductor.API.job_binary_internal_get_raw_data')
    def test_hdfs_upload_job_files(self, conductor_raw_data, remote_class,
                                   remote):
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class
        conductor_raw_data.return_value = 'ok'

        oje = FakeOozieJobEngine(u.create_cluster())
        job, _ = u.create_job_exec(edp.JOB_TYPE_PIG)
        res = oje._upload_job_files_to_hdfs(mock.Mock(), 'job_prefix', job, {})
        self.assertEqual(['job_prefix/script.pig'], res)

        job, _ = u.create_job_exec(edp.JOB_TYPE_MAPREDUCE)
        res = oje._upload_job_files_to_hdfs(mock.Mock(), 'job_prefix', job, {})
        self.assertEqual(['job_prefix/lib/main.jar'], res)

    @mock.patch('sahara.utils.remote.get_remote')
    def test_upload_workflow_file(self, remote_get):
        oje = FakeOozieJobEngine(u.create_cluster())
        remote_class = mock.MagicMock()
        remote_class.__exit__.return_value = 'closed'
        remote_get.return_value = remote_class
        res = oje._upload_workflow_file(remote_get, "test", "hadoop.xml",
                                        'hdfs')
        self.assertEqual("test/workflow.xml", res)

    @mock.patch('sahara.utils.remote.get_remote')
    def test_hdfs_create_workflow_dir(self, remote):
        remote_class = mock.MagicMock()
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class

        oje = FakeOozieJobEngine(u.create_cluster())
        job, _ = u.create_job_exec(edp.JOB_TYPE_PIG)
        res = oje._create_hdfs_workflow_dir(mock.Mock(), job)
        self.assertIn('/user/hadoop/special_name/', res)

    def test__resolve_external_hdfs_urls(self):

        oje = FakeOozieJobEngine(u.create_cluster())
        job_configs = {
            "configs": {
                "mapred.map.tasks": "1",
                "hdfs1": "hdfs://localhost/hdfs1"},
            "args": ["hdfs://localhost/hdfs3", "10"],
            "params": {
                "param1": "10",
                "param2": "hdfs://localhost/hdfs2"
            }
        }

        expected_external_hdfs_urls = ['hdfs://localhost/hdfs1',
                                       'hdfs://localhost/hdfs2',
                                       'hdfs://localhost/hdfs3']

        external_hdfs_urls = oje._resolve_external_hdfs_urls(job_configs)

        self.assertEqual(expected_external_hdfs_urls, external_hdfs_urls)

    @mock.patch('sahara.service.edp.oozie.oozie.OozieClient.get_job_info')
    @mock.patch('sahara.service.edp.oozie.oozie.OozieClient.kill_job')
    def test_cancel_job(self, kill_get, info_get):
        info_get.return_value = {}
        oje = FakeOozieJobEngine(u.create_cluster())
        _, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)

        # test cancel job without engine_job_id
        job_exec.engine_job_id = None
        oje.cancel_job(job_exec)
        self.assertEqual(0, kill_get.call_count)

        # test cancel job with engine_job_id
        job_exec.engine_job_id = 123
        oje.cancel_job(job_exec)
        self.assertEqual(1, kill_get.call_count)


class FakeOozieJobEngine(oe.OozieJobEngine):
    def get_hdfs_user(self):
        return 'hadoop'

    def create_hdfs_dir(self, remote, dir_name):
        return

    def get_oozie_server_uri(self, cluster):
        return 'http://localhost:11000/oozie'

    def get_oozie_server(self, cluster):
        return None

    def get_name_node_uri(self, cluster):
        return 'hdfs://localhost:8020'

    def get_resource_manager_uri(self, cluster):
        return 'http://localhost:50030'
