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

from unittest import mock

from sahara import context as ctx
from sahara.plugins import base as pb
from sahara.service.edp.job_utils import ds_manager
from sahara.service.edp.oozie import engine as oe
from sahara.service.edp.oozie.engine import jb_manager
from sahara.tests.unit import base
from sahara.tests.unit.service.edp import edp_test_utils as u
from sahara.utils import edp


class TestOozieEngine(base.SaharaTestCase):
    def setUp(self):
        super(TestOozieEngine, self).setUp()
        self.override_config('plugins', ['fake'])
        pb.setup_plugins()
        jb_manager.setup_job_binaries()
        ds_manager.setup_data_sources()

    def test_get_job_status(self):
        oje = FakeOozieJobEngine(u.create_cluster())
        client_class = mock.MagicMock()
        client_class.add_job = mock.MagicMock(return_value=1)
        client_class.get_job_info = mock.MagicMock(
            return_value={'status': 'PENDING'})
        oje.get_client = mock.MagicMock(return_value=client_class)

        _, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)
        self.assertIsNone(oje.get_job_status(job_exec))

        job_exec.engine_job_id = 1
        self.assertEqual({'status': 'PENDING'}, oje.get_job_status(job_exec))

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

        job_execution_type = 'scheduled'
        job_params = oje._get_oozie_job_params('hadoop',
                                               '/tmp', oozie_params, True,
                                               scheduled_params, job_dir,
                                               job_execution_type)
        for i in ["start", "end", "frequency"]:
            self.assertEqual(scheduled_params[i], job_params[i])

    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper')
    @mock.patch('sahara.conductor.API.job_binary_internal_get_raw_data')
    def test_hdfs_upload_job_files(self, conductor_raw_data, remote_class,
                                   remote):
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class
        conductor_raw_data.return_value = 'ok'

        oje = FakeOozieJobEngine(u.create_cluster())
        oje._prepare_job_binaries = mock.Mock()

        job, _ = u.create_job_exec(edp.JOB_TYPE_PIG)
        res = oje._upload_job_files_to_hdfs(mock.Mock(), 'job_prefix', job, {})
        self.assertEqual(['/tmp/script.pig'], res)

        job, _ = u.create_job_exec(edp.JOB_TYPE_MAPREDUCE)
        res = oje._upload_job_files_to_hdfs(mock.Mock(), 'job_prefix', job, {})
        self.assertEqual(['/tmp/main.jar'], res)

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
    def test_upload_coordinator_file(self, remote_get):
        oje = FakeOozieJobEngine(u.create_cluster())
        remote_class = mock.MagicMock()
        remote_class.__exit__.return_value = 'closed'
        remote_get.return_value = remote_class
        res = oje._upload_coordinator_file(remote_get, "test", "hadoop.xml",
                                           'hdfs')
        self.assertEqual("test/coordinator.xml", res)

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

    @mock.patch('sahara.service.edp.job_utils.prepare_cluster_for_ds')
    @mock.patch('sahara.service.edp.job_utils._get_data_source_urls')
    @mock.patch('sahara.service.edp.oozie.workflow_creator.'
                'workflow_factory.get_workflow_xml')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.data_source_get')
    @mock.patch('sahara.conductor.API.job_get')
    def test_prepare_run_job(self, job, data_source, update,
                             remote, wf_factory, get_ds_urls,
                             prepare_cluster):
        wf_factory.return_value = mock.MagicMock()

        remote_class = mock.MagicMock()
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class

        job_class = mock.MagicMock()
        job_class.name = "myJob"
        job.return_value = job_class

        source = mock.MagicMock()
        source.url = "localhost"

        get_ds_urls.return_value = ('url', 'url')

        data_source.return_value = source
        oje = FakeOozieJobEngine(u.create_cluster())
        _, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)
        update.return_value = job_exec

        res = oje._prepare_run_job(job_exec)
        self.assertEqual(ctx.ctx(), res['context'])
        self.assertEqual('hadoop', res['hdfs_user'])
        self.assertEqual(job_exec, res['job_execution'])
        self.assertEqual({}, res['oozie_params'])

    @mock.patch('sahara.service.edp.job_utils.prepare_cluster_for_ds')
    @mock.patch('sahara.service.edp.job_utils._get_data_source_urls')
    @mock.patch('sahara.service.edp.oozie.workflow_creator.'
                'workflow_factory.get_workflow_xml')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.data_source_get')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.conductor.API.job_execution_get')
    def test_run_job(self, exec_get, job, data_source,
                     update, remote, wf_factory, get_ds_urls,
                     prepare_cluster):
        wf_factory.return_value = mock.MagicMock()
        remote_class = mock.MagicMock()
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class

        job_class = mock.MagicMock()
        job.return_value = job_class
        job.name = "myJob"

        source = mock.MagicMock()
        source.url = "localhost"
        data_source.return_value = source

        get_ds_urls.return_value = ('url', 'url')

        oje = FakeOozieJobEngine(u.create_cluster())
        client_class = mock.MagicMock()
        client_class.add_job = mock.MagicMock(return_value=1)
        client_class.get_job_info = mock.MagicMock(
            return_value={'status': 'PENDING'})
        oje.get_client = mock.MagicMock(return_value=client_class)

        _, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)
        update.return_value = job_exec

        self.assertEqual((1, 'PENDING', None), oje.run_job(job_exec))


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
