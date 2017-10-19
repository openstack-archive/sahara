# Copyright (c) 2015 OpenStack Foundation
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

from sahara.plugins.spark import shell_engine
from sahara.service.edp.job_utils import ds_manager
from sahara.tests.unit import base
from sahara.utils import edp


class TestSparkShellEngine(base.SaharaTestCase):
    def setUp(self):
        super(TestSparkShellEngine, self).setUp()
        self.master_host = "master"
        self.master_port = 7077
        self.master_instance_id = "6789"
        self.spark_pid = "12345"
        self.spark_home = "/opt/spark"
        self.workflow_dir = "/wfdir"

        ds_manager.setup_data_sources()

    def _create_master_instance(self, return_code=0):
        master = mock.Mock()
        master.execute_command.return_value = (return_code, self.spark_pid)
        master.hostname.return_value = self.master_host
        master.id = self.master_instance_id
        return master

    def _build_cmd(self, params='', args=''):
        cmd = ('%(env_params)s%(cmd)s %(main_script)s %(args)s' % (
            {'cmd': '/bin/sh', 'main_script': 'main_script.sh',
             'env_params': params, 'args': args})
        )

        return ("cd %s; ./launch_command %s > /dev/null 2>&1 & echo $!" %
                (self.workflow_dir, cmd))

    def _check_status(self, status):
        self.assertEqual(("%s@%s" % (self.spark_pid, self.master_instance_id),
                          edp.JOB_STATUS_RUNNING,
                          {"spark-path": self.workflow_dir}), status)

    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.service.edp.job_utils.create_workflow_dir')
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.context.ctx', return_value="ctx")
    def _setup_run_job(self, master_instance, job_configs,
                       ctx, job_get, get_instance, create_workflow_dir,
                       get_remote, job_exec_get, job_exec_update):
        job = mock.Mock()
        job.name = "Spark shell job"
        job_get.return_value = job

        create_workflow_dir.return_value = self.workflow_dir

        # This is to mock "with remote.get_remote(master) as r" in run_job
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=master_instance)
        get_instance.return_value = master_instance

        eng = shell_engine.ShellEngine("cluster")
        eng._upload_job_files = mock.Mock()
        eng._upload_job_files.return_value = ['main_script.sh'], []

        job_exec = mock.Mock()
        job_exec.job_configs = job_configs
        status = eng.run_job(job_exec)

        # Check that we launch command on the master node
        get_instance.assert_called_with("cluster", self.master_host)

        return status

    def test_run_job_without_args_and_params(self):
        job_configs = {
            'configs': {},
            'args': [],
            'params': {}
        }

        master_instance = self._create_master_instance()
        status = self._setup_run_job(master_instance, job_configs)

        # Check the command
        master_instance.execute_command.assert_called_with(
            self._build_cmd())

        # Check execution status
        self._check_status(status)

    def test_run_job_with_args(self):
        job_configs = {
            'configs': {},
            'args': ['arg1', 'arg2'],
            'params': {}
        }

        master_instance = self._create_master_instance()
        status = self._setup_run_job(master_instance, job_configs)

        # Check the command
        master_instance.execute_command.assert_called_with(
            self._build_cmd(args='arg1 arg2')
        )

        # Check execution status
        self._check_status(status)

    def test_run_job_with_params(self):
        job_configs = {
            'configs': {},
            'args': [],
            'params': {'A': 'a'}
        }

        master_instance = self._create_master_instance()
        status = self._setup_run_job(master_instance, job_configs)

        # Check the command
        master_instance.execute_command.assert_called_with(
            self._build_cmd(params='A=a ')
        )

        # Check execution status
        self._check_status(status)
