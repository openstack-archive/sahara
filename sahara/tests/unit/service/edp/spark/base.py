# Copyright (c) 2014 OpenStack Foundation
# Copyright (c) 2015 ISPRAS
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

import os
from unittest import mock


import sahara.exceptions as ex
from sahara.service.edp.job_utils import ds_manager
from sahara.service.edp.spark import engine as se
from sahara.tests.unit import base
from sahara.utils import edp


class TestSpark(base.SaharaTestCase):
    def setUp(self):
        super(TestSpark, self).setUp()

        # These variables are initialized in subclasses because its values
        # depend on plugin
        self.master_host = None
        self.engine_class = None
        self.spark_user = None
        self.spark_submit = None
        self.master = None
        self.deploy_mode = None

        self.master_port = 7077
        self.master_inst = "6789"
        self.spark_pid = "12345"
        self.spark_home = "/opt/spark"
        self.workflow_dir = "/wfdir"
        self.driver_cp = "/usr/lib/hadoop-mapreduce/hadoop-openstack.jar:"

        ds_manager.setup_data_sources()

    def test_get_pid_and_inst_id(self):
        '''Test parsing of job ids

        Test that job ids of the form pid@instance are
        split into pid and instance ids by eng._get_pid_and_inst_id()
        but anything else returns empty strings
        '''
        eng = se.SparkJobEngine(None)
        for job_id in [None, "", "@", "something", "pid@", "@instance"]:
            pid, inst_id = eng._get_pid_and_inst_id(job_id)
            self.assertEqual(("", ""), (pid, inst_id))

        pid, inst_id = eng._get_pid_and_inst_id("pid@instance")
        self.assertEqual(("pid", "instance"), (pid, inst_id))

    @mock.patch('sahara.utils.cluster.get_instances')
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

        job_exec.engine_job_id = "invalid id"
        self.assertEqual((None, None),
                         eng._get_instance_if_running(job_exec))

        job_exec.engine_job_id = "pid@inst_id"
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
        self.assertIsNone(instance)

        # Pretend get_instances throws an exception
        get_instances.side_effect = Exception("some failure")
        pid, instance = eng._get_instance_if_running(job_exec)
        self.assertIsNone(instance)

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
        self.assertEqual(999, ret)

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
        self.assertIsNone(status)

        # Pretend we have an instance
        _get_instance_if_running.return_value = "pid", "instance"
        _get_job_status_from_remote.return_value = {"status":
                                                    edp.JOB_STATUS_RUNNING}
        status = eng.get_job_status(job_exec)
        _get_job_status_from_remote.assert_called_with(eng,
                                                       remote_instance,
                                                       "pid", job_exec)
        self.assertEqual({"status": edp.JOB_STATUS_RUNNING}, status)

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

        self.assertEqual({"status": edp.JOB_STATUS_KILLED}, status)

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
        self.assertEqual(0, _get_job_status_from_remote.called)

        # check that we have nothing new to report ...
        self.assertIsNone(status)

    @mock.patch('sahara.service.edp.spark.engine.jb_manager')
    @mock.patch('sahara.utils.remote.get_remote')
    def test_upload_job_files(self, get_remote, jb_manager):
        main_names = ["main1", "main2", "main3"]
        lib_names = ["lib1", "lib2", "lib3"]

        def make_data_objects(*args):
            objs = []
            for name in args:
                m = mock.Mock()
                m.name = name
                objs.append(m)
            return objs

        job = mock.Mock()
        job.name = "job"
        job.mains = make_data_objects(*main_names)
        job.libs = make_data_objects(*lib_names)

        # This is to mock "with remote.get_remote(instance) as r"
        remote_instance = mock.Mock()
        remote_instance.instance.node_group.cluster.shares = []
        remote_instance.instance.node_group.shares = []
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=remote_instance)

        JOB_BINARIES = mock.Mock()
        mock_jb = mock.Mock()
        jb_manager.JOB_BINARIES = JOB_BINARIES

        JOB_BINARIES.get_job_binary_by_url = mock.Mock(return_value=mock_jb)

        mock_jb.copy_binary_to_cluster = mock.Mock(side_effect=[
                                                   '/somedir/main1',
                                                   '/somedir/main2',
                                                   '/somedir/main3',
                                                   '/somedir/lib1',
                                                   '/somedir/lib2',
                                                   '/somedir/lib3'])

        eng = se.SparkJobEngine("cluster")
        eng._prepare_job_binaries = mock.Mock()

        paths, builtins = eng._upload_job_files("where", "/somedir", job, {})
        self.assertEqual(["/somedir/" + n for n in main_names + lib_names],
                         paths)

    def _make_master_instance(self, return_code=0):
        master = mock.Mock()
        master.execute_command.return_value = (return_code, self.spark_pid)
        master.get_python_version.return_value = 'python'
        master.hostname.return_value = self.master_host
        master.id = self.master_inst
        return master

    def _config_values(self, *key):
        return {("Spark", "Master port", "cluster"): self.master_port,
                ("Spark", "Spark home", "cluster"): self.spark_home,
                ("Spark", "Executor extra classpath",
                 "cluster"): self.driver_cp}[key]

    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.plugins.utils.get_config_value_or_default')
    @mock.patch('sahara.service.edp.job_utils.create_workflow_dir')
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.context.ctx', return_value="ctx")
    def _setup_run_job(self, master_instance, job_configs, files,
                       ctx, job_get, get_instance, create_workflow_dir,
                       get_config_value, get_remote, job_exec_get,
                       job_exec_update):

        def _upload_job_files(where, job_dir, job,
                              libs_subdir=True, job_configs=None):
            paths = [os.path.join(self.workflow_dir, f) for f in files['jars']]
            bltns = files.get('bltns', [])
            bltns = [os.path.join(self.workflow_dir, f) for f in bltns]
            return paths, bltns

        job = mock.Mock()
        job.name = "MyJob"
        job_get.return_value = job

        job_exec = mock.Mock()
        job_exec.job_configs = job_configs

        get_config_value.side_effect = self._config_values

        create_workflow_dir.return_value = self.workflow_dir

        # This is to mock "with remote.get_remote(master) as r" in run_job
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=master_instance)
        get_instance.return_value = master_instance

        eng = self.engine_class("cluster")
        eng._upload_job_files = mock.Mock()
        eng._upload_job_files.side_effect = _upload_job_files
        status = eng.run_job(job_exec)

        # Check that we launch on the master node
        get_instance.assert_called_with("cluster", self.master_host)

        return status

    def test_run_job_raise(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass"},
            'args': ['input_arg', 'output_arg']
        }

        files = {'jars': ["app.jar",
                          "jar1.jar",
                          "jar2.jar"]}

        # The object representing the spark master node
        # The spark-submit command will be run on this instance
        master_instance = self._make_master_instance(return_code=1)

        # If execute_command returns an error we should get a raise
        self.assertRaises(ex.EDPError,
                          self._setup_run_job,
                          master_instance, job_configs, files)

    def test_run_job_extra_jars_args(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass"},
            'args': ['input_arg', 'output_arg']
        }

        files = {'jars': ["app.jar",
                          "jar1.jar",
                          "jar2.jar"]}

        # The object representing the spark master node
        # The spark-submit command will be run on this instance
        master_instance = self._make_master_instance()
        status = self._setup_run_job(master_instance, job_configs, files)

        # Check the command
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command %(spark_user)s%(spark_submit)s '
            '--class org.me.myclass --jars jar1.jar,jar2.jar '
            '--master %(master)s '
            '--deploy-mode %(deploy_mode)s '
            'app.jar input_arg output_arg '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "spark_user": self.spark_user,
                                            "spark_submit": self.spark_submit,
                                            "master": self.master,
                                            "deploy_mode": self.deploy_mode})

        # Check result here
        self.assertEqual(("%s@%s" % (self.spark_pid, self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"spark-path": self.workflow_dir}), status)

    def test_run_job_args(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass"},
            'args': ['input_arg', 'output_arg']
        }

        files = {'jars': ["app.jar"]}

        # The object representing the spark master node
        # The spark-submit command will be run on this instance
        master_instance = self._make_master_instance()
        status = self._setup_run_job(master_instance, job_configs, files)

        # Check the command
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command %(spark_user)s%(spark_submit)s '
            '--class org.me.myclass '
            '--master %(master)s '
            '--deploy-mode %(deploy_mode)s '
            'app.jar input_arg output_arg '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "spark_user": self.spark_user,
                                            "spark_submit": self.spark_submit,
                                            "master": self.master,
                                            "deploy_mode": self.deploy_mode})

        # Check result here
        self.assertEqual(("%s@%s" % (self.spark_pid, self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"spark-path": self.workflow_dir}), status)

    def test_run_job(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass"},
        }

        files = {'jars': ["app.jar"]}

        # The object representing the spark master node
        # The spark-submit command will be run on this instance
        master_instance = self._make_master_instance()
        status = self._setup_run_job(master_instance, job_configs, files)

        # Check the command
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command %(spark_user)s%(spark_submit)s '
            '--class org.me.myclass '
            '--master %(master)s '
            '--deploy-mode %(deploy_mode)s '
            'app.jar '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "spark_user": self.spark_user,
                                            "spark_submit": self.spark_submit,
                                            "master": self.master,
                                            "deploy_mode": self.deploy_mode})

        # Check result here
        self.assertEqual(("%s@%s" % (self.spark_pid, self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"spark-path": self.workflow_dir}), status)

    def test_run_job_wrapper_extra_jars_args(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass",
                        "edp.spark.adapt_for_swift": True},
            'args': ['input_arg', 'output_arg']
        }

        files = {'jars': ["app.jar",
                          "jar1.jar",
                          "jar2.jar"],
                 'bltns': ["wrapper.jar"]}

        # The object representing the spark master node
        # The spark-submit command will be run on this instance
        master_instance = self._make_master_instance()
        status = self._setup_run_job(master_instance, job_configs, files)

        # Check the command
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command %(spark_user)s%(spark_submit)s '
            '--driver-class-path %(driver_cp)s '
            '--files spark.xml '
            '--class org.openstack.sahara.edp.SparkWrapper '
            '--jars wrapper.jar,jar1.jar,jar2.jar '
            '--master %(master)s '
            '--deploy-mode %(deploy_mode)s '
            'app.jar spark.xml org.me.myclass input_arg output_arg '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "spark_user": self.spark_user,
                                            "spark_submit": self.spark_submit,
                                            "driver_cp": self.driver_cp,
                                            "master": self.master,
                                            "deploy_mode": self.deploy_mode})

        # Check result here
        self.assertEqual(("%s@%s" % (self.spark_pid, self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"spark-path": self.workflow_dir}), status)

    def test_run_job_wrapper_args(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass",
                        "edp.spark.adapt_for_swift": True},
            'args': ['input_arg', 'output_arg']
        }

        files = {'jars': ["app.jar"],
                 'bltns': ["wrapper.jar"]}

        # The object representing the spark master node
        # The spark-submit command will be run on this instance
        master_instance = self._make_master_instance()
        status = self._setup_run_job(master_instance, job_configs, files)

        # Check the command
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command %(spark_user)s%(spark_submit)s '
            '--driver-class-path %(driver_cp)s '
            '--files spark.xml '
            '--class org.openstack.sahara.edp.SparkWrapper '
            '--jars wrapper.jar '
            '--master %(master)s '
            '--deploy-mode %(deploy_mode)s '
            'app.jar spark.xml org.me.myclass input_arg output_arg '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "spark_user": self.spark_user,
                                            "spark_submit": self.spark_submit,
                                            "driver_cp": self.driver_cp,
                                            "master": self.master,
                                            "deploy_mode": self.deploy_mode})

        # Check result here
        self.assertEqual(("%s@%s" % (self.spark_pid, self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"spark-path": self.workflow_dir}), status)

    def test_run_job_wrapper(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass",
                        "edp.spark.adapt_for_swift": True}
        }

        files = {'jars': ["app.jar"],
                 'bltns': ["wrapper.jar"]}

        # The object representing the spark master node
        # The spark-submit command will be run on this instance
        master_instance = self._make_master_instance()
        status = self._setup_run_job(master_instance, job_configs, files)

        # Check the command
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command %(spark_user)s%(spark_submit)s '
            '--driver-class-path %(driver_cp)s '
            '--files spark.xml '
            '--class org.openstack.sahara.edp.SparkWrapper '
            '--jars wrapper.jar '
            '--master %(master)s '
            '--deploy-mode %(deploy_mode)s '
            'app.jar spark.xml org.me.myclass '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "spark_user": self.spark_user,
                                            "spark_submit": self.spark_submit,
                                            "driver_cp": self.driver_cp,
                                            "master": self.master,
                                            "deploy_mode": self.deploy_mode})

        # Check result here
        self.assertEqual(("%s@%s" % (self.spark_pid, self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"spark-path": self.workflow_dir}), status)

    @mock.patch('sahara.service.edp.job_utils.prepare_cluster_for_ds')
    @mock.patch('sahara.service.edp.job_utils.resolve_data_source_references')
    def test_external_hdfs_config(self, resolver, prepare):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass"},
        }

        files = {'jars': ["app.jar"]}

        data_source = mock.Mock()
        data_source.type = 'hdfs'
        data_source.id = 'id'
        resolver.return_value = ([data_source], job_configs)

        master_instance = self._make_master_instance()
        self._setup_run_job(master_instance, job_configs, files)

        prepare.assert_called_once()

    @mock.patch('sahara.service.edp.job_utils.prepare_cluster_for_ds')
    @mock.patch('sahara.service.edp.job_utils.resolve_data_source_references')
    def test_overridden_driver_classpath(self, resolver, prepare):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass",
                        'edp.spark.driver.classpath': "my-classpath.jar"},
        }

        files = {'jars': ["app.jar"]}

        data_source = mock.Mock()
        data_source.type = 'hdfs'
        data_source.id = 'id'
        resolver.return_value = ([data_source], job_configs)

        master_instance = self._make_master_instance()
        self._setup_run_job(master_instance, job_configs, files)

        # check that overridden value was applied
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command %(spark_user)s%(spark_submit)s '
            '--driver-class-path my-classpath.jar '
            '--class org.me.myclass '
            '--master %(master)s '
            '--deploy-mode %(deploy_mode)s '
            'app.jar '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "spark_user": self.spark_user,
                                            "spark_submit": self.spark_submit,
                                            "master": self.master,
                                            "deploy_mode": self.deploy_mode})
