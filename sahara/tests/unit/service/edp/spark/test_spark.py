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

import sahara.exceptions as ex
from sahara.service.edp.spark import engine as se
from sahara.tests.unit import base
from sahara.utils import edp


class TestSpark(base.SaharaTestCase):
    def setUp(self):
        super(TestSpark, self).setUp()

    def test_get_pid_and_inst_id(self):
        '''Test parsing of job ids

        Test that job ids of the form pid@instance are
        split into pid and instance ids by eng._get_pid_and_inst_id()
        but anything else returns empty strings
        '''
        eng = se.SparkJobEngine(None)
        for job_id in [None, "", "@", "something", "pid@", "@instance"]:
            pid, inst_id = eng._get_pid_and_inst_id(job_id)
            self.assertEqual((pid, inst_id), ("", ""))

        pid, inst_id = eng._get_pid_and_inst_id("pid@instance")
        self.assertEqual(("pid", "instance"), (pid, inst_id))

    @mock.patch('sahara.utils.general.get_instances')
    def test_get_instance_if_running(self, get_instances):
        '''Test retrieval of pid and instance object for running job

        If the job id is valid and the job status is non-terminated,
        _get_instance_if_running() should retrieve the instance
        based on the inst_id and return the pid and instance.

        If the job is invalid or the job is terminated, it should
        return None, None.

        If get_instances() throws an exception or returns an empty list,
        the instance returned should be None (pid might still be set)
        '''
        get_instances.return_value = ["instance"]
        job_exec = mock.Mock()
        eng = se.SparkJobEngine("cluster")

        job_exec.oozie_job_id = "invalid id"
        self.assertEqual((None, None),
                         eng._get_instance_if_running(job_exec))

        job_exec.oozie_job_id = "pid@inst_id"
        for state in edp.JOB_STATUSES_TERMINATED:
            job_exec.info = {'status': state}
            self.assertEqual((None, None),
                             eng._get_instance_if_running(job_exec))

        job_exec.info = {'status': edp.JOB_STATUS_RUNNING}
        self.assertEqual(("pid", "instance"),
                         eng._get_instance_if_running(job_exec))
        get_instances.assert_called_with("cluster", ["inst_id"])

        # Pretend get_instances returns nothing
        get_instances.return_value = []
        pid, instance = eng._get_instance_if_running(job_exec)
        self.assertEqual(instance, None)

        # Pretend get_instances throws an exception
        get_instances.side_effect = Exception("some failure")
        pid, instance = eng._get_instance_if_running(job_exec)
        self.assertEqual(instance, None)

    def test_get_result_file(self):
        remote = mock.Mock()
        remote.execute_command.return_value = 999, "value"
        job_exec = mock.Mock()
        job_exec.extra = {"spark-path": "/tmp/spark-edp/Job/123"}

        eng = se.SparkJobEngine("cluster")
        ret, stdout = eng._get_result_file(remote, job_exec)
        remote.execute_command.assert_called_with(
            "cat /tmp/spark-edp/Job/123/result",
            raise_when_error=False)
        self.assertEqual((ret, stdout),
                         remote.execute_command.return_value)

    def test_check_pid(self):
        remote = mock.Mock()
        remote.execute_command.return_value = 999, ""

        eng = se.SparkJobEngine("cluster")
        ret = eng._check_pid(remote, "pid")
        remote.execute_command.assert_called_with("ps hp pid",
                                                  raise_when_error=False)
        self.assertEqual(ret, 999)

    @mock.patch.object(se.SparkJobEngine,
                       '_get_result_file',
                       autospec=True)
    @mock.patch.object(se.SparkJobEngine,
                       '_check_pid',
                       autospec=True)
    def test_get_job_status_from_remote(self, _check_pid, _get_result_file):
        '''Test retrieval of job status from remote instance

        If the process is present, status is RUNNING
        If the process is not present, status depends on the result file
        If the result file is missing, status is DONEWITHERROR
        '''
        eng = se.SparkJobEngine("cluster")
        job_exec = mock.Mock()
        remote = mock.Mock()

        # Pretend process is running
        _check_pid.return_value = 0
        status = eng._get_job_status_from_remote(remote, "pid", job_exec)
        _check_pid.assert_called_with(eng, remote, "pid")
        self.assertEqual({"status": edp.JOB_STATUS_RUNNING}, status)

        # Pretend process ended and result file contains 0 (success)
        _check_pid.return_value = 1
        _get_result_file.return_value = 0, "0"
        status = eng._get_job_status_from_remote(remote, "pid", job_exec)
        self.assertEqual({"status": edp.JOB_STATUS_SUCCEEDED}, status)

        # Pretend process ended and result file contains 1 (success)
        _get_result_file.return_value = 0, "1"
        status = eng._get_job_status_from_remote(remote, "pid", job_exec)
        self.assertEqual({"status": edp.JOB_STATUS_DONEWITHERROR}, status)

        # Pretend process ended and result file contains 130 (killed)
        _get_result_file.return_value = 0, "130"
        status = eng._get_job_status_from_remote(remote, "pid", job_exec)
        self.assertEqual({"status": edp.JOB_STATUS_KILLED}, status)

        # Pretend process ended and result file contains -2 (killed)
        _get_result_file.return_value = 0, "-2"
        status = eng._get_job_status_from_remote(remote, "pid", job_exec)
        self.assertEqual({"status": edp.JOB_STATUS_KILLED}, status)

        # Pretend process ended and result file is missing
        _get_result_file.return_value = 1, ""
        status = eng._get_job_status_from_remote(remote, "pid", job_exec)
        self.assertEqual({"status": edp.JOB_STATUS_DONEWITHERROR}, status)

    @mock.patch.object(se.SparkJobEngine,
                       '_get_job_status_from_remote',
                       autospec=True)
    @mock.patch.object(se.SparkJobEngine,
                       '_get_instance_if_running',
                       autospec=True)
    @mock.patch('sahara.utils.remote.get_remote')
    def test_get_job_status(self,
                            get_remote,
                            _get_instance_if_running,
                            _get_job_status_from_remote):

        # This is to mock "with remote.get_remote(instance) as r"
        remote_instance = mock.Mock()
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=remote_instance)

        # Pretend instance is not returned
        _get_instance_if_running.return_value = "pid", None
        job_exec = mock.Mock()
        eng = se.SparkJobEngine("cluster")
        status = eng.get_job_status(job_exec)
        self.assertEqual(status, None)

        # Pretend we have an instance
        _get_instance_if_running.return_value = "pid", "instance"
        _get_job_status_from_remote.return_value = {"status":
                                                    edp.JOB_STATUS_RUNNING}
        status = eng.get_job_status(job_exec)
        _get_job_status_from_remote.assert_called_with(eng,
                                                       remote_instance,
                                                       "pid", job_exec)
        self.assertEqual(status, {"status": edp.JOB_STATUS_RUNNING})

    @mock.patch.object(se.SparkJobEngine,
                       '_get_instance_if_running',
                       autospec=True,
                       return_value=(None, None))
    @mock.patch('sahara.utils.remote.get_remote')
    def test_cancel_job_null_or_done(self,
                                     get_remote,
                                     _get_instance_if_running):
        '''Test cancel_job() when instance is None

        Test that cancel_job() returns None and does not try to
        retrieve a remote instance if _get_instance_if_running() returns None
        '''
        eng = se.SparkJobEngine("cluster")
        job_exec = mock.Mock()
        self.assertIsNone(eng.cancel_job(job_exec))
        self.assertTrue(_get_instance_if_running.called)
        self.assertFalse(get_remote.called)

    @mock.patch.object(se.SparkJobEngine,
                       '_get_job_status_from_remote',
                       autospec=True,
                       return_value={"status": edp.JOB_STATUS_KILLED})
    @mock.patch.object(se.SparkJobEngine,
                       '_get_instance_if_running',
                       autospec=True,
                       return_value=("pid", "instance"))
    @mock.patch('sahara.utils.remote.get_remote')
    def test_cancel_job(self,
                        get_remote,
                        _get_instance_if_running,
                        _get_job_status_from_remote):
        '''Test cancel_job() with a valid instance

        For a valid instance, test that cancel_job:

        * retrieves the remote instance
        * executes the proper kill command
        * retrieves the job status (because the remote command is successful)
        '''

        # This is to mock "with remote.get_remote(instance) as r" in cancel_job
        # and to mock r.execute_command to return success
        remote_instance = mock.Mock()
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=remote_instance)
        remote_instance.execute_command.return_value = (0, "standard out")

        eng = se.SparkJobEngine("cluster")
        job_exec = mock.Mock()
        status = eng.cancel_job(job_exec)

        # check that remote.get_remote was called with the result of
        # eng._get_instance_if_running()
        get_remote.assert_called_with("instance")

        # check that execute_command was called with the proper arguments
        # ("pid" was passed in)
        remote_instance.execute_command.assert_called_with(
            "kill -SIGINT pid",
            raise_when_error=False)

        # check that the job status was retrieved since the command succeeded
        _get_job_status_from_remote.assert_called_with(eng,
                                                       remote_instance,
                                                       "pid", job_exec)

        self.assertEqual(status, {"status": edp.JOB_STATUS_KILLED})

    @mock.patch.object(se.SparkJobEngine,
                       '_get_job_status_from_remote',
                       autospec=True)
    @mock.patch.object(se.SparkJobEngine,
                       '_get_instance_if_running',
                       autospec=True,
                       return_value=("pid", "instance"))
    @mock.patch('sahara.utils.remote.get_remote')
    def test_cancel_job_failed(self,
                               get_remote,
                               _get_instance_if_running,
                               _get_job_status_from_remote):
        '''Test cancel_job() when remote command fails

        For a valid instance and a failed kill command, test that cancel_job:

        * retrieves the remote instance
        * executes the proper kill command
        * does not retrieve the job status (because the remote command failed)
        '''

        # This is to mock "with remote.get_remote(instance) as r"
        # and to mock r.execute_command to return failure
        remote_instance = mock.Mock()
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=remote_instance)
        remote_instance.execute_command.return_value = (-1, "some error")

        eng = se.SparkJobEngine("cluster")
        job_exec = mock.Mock()
        status = eng.cancel_job(job_exec)

        # check that remote.get_remote was called with the result of
        # eng._get_instance_if_running
        get_remote.assert_called_with("instance")

        # check that execute_command was called with the proper arguments
        # ("pid" was passed in)
        remote_instance.execute_command.assert_called_with(
            "kill -SIGINT pid",
            raise_when_error=False)

        # check that the job status was not retrieved since the command failed
        self.assertEqual(_get_job_status_from_remote.called, 0)

        # check that we have nothing new to report ...
        self.assertEqual(status, None)

    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.plugins.spark.config_helper.get_config_value')
    @mock.patch('sahara.service.edp.job_utils.upload_job_files',
                return_value=["/wfdir/app.jar",
                              "/wfdir/jar1.jar",
                              "/wfdir/jar2.jar"])
    @mock.patch('sahara.service.edp.job_utils.create_workflow_dir',
                return_value="/wfdir")
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.context.ctx', return_value="ctx")
    def test_run_job(self, ctx, job_get, get_instance, create_workflow_dir,
                     upload_job_files, get_config_value, get_remote,
                     job_exec_get):

        def fix_get(field, default=None):
            if field == "args":
                return ["input_arg", "output_arg"]
            return default

        eng = se.SparkJobEngine("cluster")

        job = mock.Mock()
        job.name = "MyJob"
        job_get.return_value = job

        job_exec = mock.Mock()
        job_exec.job_configs.configs = {"edp.java.main_class":
                                        "org.me.myclass"}
        job_exec.job_configs.get = fix_get

        master = mock.Mock()
        get_instance.return_value = master
        master.hostname.return_value = "master"
        master.id = "6789"

        get_config_value.side_effect = lambda *x: {
            ("Spark", "Master port", "cluster"): 7077,
            ("Spark", "Spark home", "cluster"): "/opt/spark"}[x]

        # This is to mock "with remote.get_remote(master) as r" in run_job
        remote_instance = mock.Mock()
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=remote_instance)
        remote_instance.execute_command.return_value = (0, "12345")

        status = eng.run_job(job_exec)

        # Check that we launch on the master node
        get_instance.assert_called_with("cluster", "master")

        # Check the command
        remote_instance.execute_command.assert_called_with(
            'cd /wfdir; ./launch_command /opt/spark/bin/spark-submit app.jar '
            '--class org.me.myclass --jars jar1.jar,jar2.jar '
            '--master spark://master:7077 input_arg output_arg '
            '> /dev/null 2>&1 & echo $!')

        # Check result here
        self.assertEqual(status, ("12345@6789",
                                  edp.JOB_STATUS_RUNNING,
                                  {"spark-path": "/wfdir"}))

        # Run again without support jars.  Note the extra space
        # after 'myclass', this is from a %s with empty string
        upload_job_files.return_value = ["/wfdir/app.jar"]
        status = eng.run_job(job_exec)
        remote_instance.execute_command.assert_called_with(
            'cd /wfdir; ./launch_command /opt/spark/bin/spark-submit app.jar '
            '--class org.me.myclass  '
            '--master spark://master:7077 input_arg output_arg '
            '> /dev/null 2>&1 & echo $!')

        # run again with non-zero result, should raise EDPError
        remote_instance.execute_command.return_value = (1, "some_error")
        self.assertRaises(ex.EDPError, eng.run_job, job_exec)
