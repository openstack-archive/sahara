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
        job_params = oje._get_oozie_job_params('hadoop',
                                               '/tmp', oozie_params, True)
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
    def test_hdfs_create_workflow_dir(self, remote):
        remote_class = mock.MagicMock()
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class

        oje = FakeOozieJobEngine(u.create_cluster())
        job, _ = u.create_job_exec(edp.JOB_TYPE_PIG)
        res = oje._create_hdfs_workflow_dir(mock.Mock(), job)
        self.assertIn('/user/hadoop/special_name/', res)


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
