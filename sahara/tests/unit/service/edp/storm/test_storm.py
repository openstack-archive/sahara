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

import os
from unittest import mock


import sahara.exceptions as ex
from sahara.service.edp.job_utils import ds_manager
from sahara.service.edp.storm import engine as se
from sahara.service.edp.storm.engine import jb_manager
from sahara.tests.unit import base
from sahara.utils import edp


class TestStorm(base.SaharaTestCase):
    def setUp(self):
        super(TestStorm, self).setUp()

        self.master_host = "master"
        self.master_inst = "6789"
        self.storm_topology_name = "MyJob_ed8347a9-39aa-477c-8108-066202eb6130"
        self.workflow_dir = "/wfdir"

        jb_manager.setup_job_binaries()
        ds_manager.setup_data_sources()

    def test_get_topology_and_inst_id(self):
        '''Test parsing of job ids

        Test that job ids of the form topology_name@instance are
        split into topology_name and instance ids by
        eng._get_topology_name_and_inst_id() but anything else
        returns empty strings
        '''
        eng = se.StormJobEngine(None)
        for job_id in [None, "", "@", "something", "topology_name@",
                       "@instance"]:
            topology_name, inst_id = eng._get_topology_and_inst_id(job_id)
            self.assertEqual(("", ""), (topology_name, inst_id))

        topology_name, inst_id = eng._get_topology_and_inst_id(
            "topology_name@instance")
        self.assertEqual(("topology_name", "instance"),
                         (topology_name, inst_id))

    @mock.patch('sahara.utils.cluster.get_instances')
    def test_get_instance_if_running(self, get_instances):
        '''Test retrieval of topology_name and instance object for running job

        If the job id is valid and the job status is non-terminated,
        _get_instance_if_running() should retrieve the instance
        based on the inst_id and return the topology_name and instance.

        If the job is invalid or the job is terminated, it should
        return None, None.

        If get_instances() throws an exception or returns an empty list,
        the instance returned should be None (topology_name might
        still be set)
        '''
        get_instances.return_value = ["instance"]
        job_exec = mock.Mock()
        eng = se.StormJobEngine("cluster")

        job_exec.engine_job_id = "invalid id"
        self.assertEqual((None, None),
                         eng._get_instance_if_running(job_exec))

        job_exec.engine_job_id = "topology_name@inst_id"
        for state in edp.JOB_STATUSES_TERMINATED:
            job_exec.info = {'status': state}
            self.assertEqual((None, None),
                             eng._get_instance_if_running(job_exec))

        job_exec.info = {'status': edp.JOB_STATUS_RUNNING}
        self.assertEqual(("topology_name", "instance"),
                         eng._get_instance_if_running(job_exec))
        get_instances.assert_called_with("cluster", ["inst_id"])

        # Pretend get_instances returns nothing
        get_instances.return_value = []
        topology_name, instance = eng._get_instance_if_running(job_exec)
        self.assertIsNone(instance)

        # Pretend get_instances throws an exception
        get_instances.side_effect = Exception("some failure")
        topology_name, instance = eng._get_instance_if_running(job_exec)
        self.assertIsNone(instance)

    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.utils.cluster.get_instances')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.context.ctx', return_value="ctx")
    def test_get_job_status_from_remote(self, get_instance, get_instances,
                                        get_remote, ctx, job_get):
        '''Test retrieval of job status from remote instance

        If the process is present, status is RUNNING
        If the process is not present, status depends on the result file
        If the result file is missing, status is DONEWITHERROR
        '''
        eng = se.StormJobEngine("cluster")
        job_exec = mock.Mock()

        master_instance = self._make_master_instance()
        master_instance.execute_command.return_value = 0, "ACTIVE"
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=master_instance)
        get_instance.return_value = master_instance
        get_instances.return_value = ["instance"]

        # Pretend process is running
        job_exec.engine_job_id = "topology_name@inst_id"
        job_exec.info = {'status': edp.JOB_STATUS_RUNNING}
        job_exec.job_configs = {"configs": {"topology_name": "topology_name"}}
        status = eng._get_job_status_from_remote(job_exec)
        self.assertEqual({"status": edp.JOB_STATUS_RUNNING}, status)

    @mock.patch.object(se.StormJobEngine,
                       '_get_job_status_from_remote',
                       autospec=True)
    @mock.patch.object(se.StormJobEngine,
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
        _get_instance_if_running.return_value = "topology_name", None
        job_exec = mock.Mock()
        eng = se.StormJobEngine("cluster")
        status = eng.get_job_status(job_exec)
        self.assertIsNone(status)

        # Pretend we have an instance
        _get_instance_if_running.return_value = "topology_name", "instance"
        _get_job_status_from_remote.return_value = {"status":
                                                    edp.JOB_STATUS_RUNNING}
        status = eng.get_job_status(job_exec)
        _get_job_status_from_remote.assert_called_with(eng,
                                                       job_exec, 3)
        self.assertEqual({"status": edp.JOB_STATUS_RUNNING}, status)

    @mock.patch.object(se.StormJobEngine,
                       '_get_instance_if_running',
                       autospec=True,
                       return_value=(None, None))
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.context.ctx', return_value="ctx")
    def test_cancel_job_null_or_done(self,
                                     get_remote,
                                     _get_instance_if_running,
                                     job_get,
                                     ctx):
        '''Test cancel_job() when instance is None

        Test that cancel_job() returns None and does not try to
        retrieve a remote instance if _get_instance_if_running() returns None
        '''
        eng = se.StormJobEngine("cluster")
        job_exec = mock.Mock()
        self.assertIsNone(eng.cancel_job(job_exec))
        self.assertFalse(get_remote.called)

    @mock.patch.object(se.StormJobEngine,
                       '_get_job_status_from_remote',
                       autospec=True,
                       return_value={"status": edp.JOB_STATUS_KILLED})
    @mock.patch('sahara.utils.cluster.get_instances')
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.utils.remote.get_remote')
    def test_cancel_job(self, get_remote, get_instance, get_instances,
                        _get_job_status_from_remote):
        master_instance = self._make_master_instance()
        status = self._setup_tests(master_instance)
        get_instance.return_value = master_instance
        get_instances.return_value = ["instance"]
        master_instance.execute_command.return_value = 0, "KILLED"

        get_remote.return_value.__enter__ = mock.Mock(
            return_value=master_instance)
        eng = se.StormJobEngine("cluster")
        job_exec = mock.Mock()
        job_exec.engine_job_id = "topology_name@inst_id"
        job_exec.info = {'status': edp.JOB_STATUS_RUNNING}
        job_exec.job_configs = {"configs": {"topology_name": "topology_name"}}
        status = eng.cancel_job(job_exec)

        master_instance.execute_command.assert_called_with(
            "/usr/local/storm/bin/storm kill -c nimbus.host=%s topology_name "
            "> /dev/null 2>&1 & echo $!" % self.master_host)

        self.assertEqual({"status": edp.JOB_STATUS_KILLED}, status)

    @mock.patch('sahara.service.edp.storm.engine.jb_manager')
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
        job.id = "job_exec_id"
        job.mains = make_data_objects(*main_names)
        job.libs = make_data_objects(*lib_names)

        # This is to mock "with remote.get_remote(instance) as r"
        remote_instance = mock.Mock()
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=remote_instance)
        remote_instance.instance.node_group.cluster.shares = []
        remote_instance.instance.node_group.shares = []

        JOB_BINARIES = mock.Mock()
        mock_jb = mock.Mock()
        jb_manager.JOB_BINARIES = JOB_BINARIES

        JOB_BINARIES.get_job_binary_by_url = mock.Mock(return_value=mock_jb)

        jbs = main_names + lib_names

        mock_jb.copy_binary_to_cluster = mock.Mock(
            side_effect=['/tmp/%s.%s' % (job.id, j) for j in jbs])

        eng = se.StormJobEngine("cluster")
        eng._prepare_job_binaries = mock.Mock()

        paths = eng._upload_job_files("where", "/somedir", job, {})
        self.assertEqual(['/tmp/%s.%s' % (job.id, j) for j in jbs],
                         paths)

    def _make_master_instance(self, return_code=0):
        master = mock.Mock()
        master.execute_command.return_value = (return_code,
                                               self.storm_topology_name)
        master.get_python_version.return_value = 'python'
        master.hostname.return_value = self.master_host
        master.id = self.master_inst
        return master

    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.context.ctx', return_value="ctx")
    def _setup_tests(self, master_instance, ctx, job_get,
                     get_instance, get_remote, job_exec_get):

        # This is to mock "with remote.get_remote(master) as r" in run_job
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=master_instance)
        get_instance.return_value = master_instance

    @mock.patch.object(se.StormJobEngine,
                       '_generate_topology_name',
                       autospec=True,
                       return_value=(
                           "MyJob_ed8347a9-39aa-477c-8108-066202eb6130"))
    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.service.edp.job_utils.create_workflow_dir')
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.context.ctx', return_value="ctx")
    def _setup_run_job(self, master_instance, job_configs, files,
                       ctx, job_get, get_instance, create_workflow_dir,
                       get_remote, job_exec_get, job_exec_update,
                       _generate_topology_name):

        def _upload_job_files(where, job_dir, job,
                              libs_subdir=True, job_configs=None):
            paths = [os.path.join(self.workflow_dir, f) for f in files['jars']]
            return paths

        job = mock.Mock()
        job.name = "MyJob"
        job_get.return_value = job

        job_exec = mock.Mock()
        job_exec.job_configs = job_configs

        create_workflow_dir.return_value = self.workflow_dir

        # This is to mock "with remote.get_remote(master) as r" in run_job
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=master_instance)
        get_instance.return_value = master_instance

        eng = se.StormJobEngine("cluster")
        eng._upload_job_files = mock.Mock()
        eng._upload_job_files.side_effect = _upload_job_files
        status = eng.run_job(job_exec)

        # Check that we launch on the master node
        get_instance.assert_called_with("cluster", "nimbus")

        return status

    def test_run_job_raise(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass",
                        "topology_name": "topology_name"},
        }

        files = {'jars': ["app.jar"]}

        # The object representing the storm master node
        # The storm jar command will be run on this instance
        master_instance = self._make_master_instance(return_code=1)

        # If execute_command returns an error we should get a raise
        self.assertRaises(ex.EDPError,
                          self._setup_run_job,
                          master_instance, job_configs, files)

    def test_run_job(self):
        job_configs = {
            'configs': {"edp.java.main_class": "org.me.myclass"}
        }

        files = {'jars': ["app.jar"]}

        # The object representing the storm master node
        # The storm jar command will be run on this instance
        master_instance = self._make_master_instance()
        status = self._setup_run_job(master_instance, job_configs, files)

        # Check the command
        master_instance.execute_command.assert_called_with(
            'cd %(workflow_dir)s; '
            './launch_command /usr/local/storm/bin/storm jar '
            '-c nimbus.host=master '
            '%(workflow_dir)s/app.jar org.me.myclass %(topology_name)s '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "topology_name": (
                                                self.storm_topology_name)})

        # Check result here
        self.assertEqual(("%s@%s" % (self.storm_topology_name,
                                     self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"storm-path": self.workflow_dir}), status)

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
            './launch_command /usr/local/storm/bin/storm jar '
            '-c nimbus.host=master '
            '%(workflow_dir)s/app.jar org.me.myclass %(topology_name)s '
            'input_arg output_arg '
            '> /dev/null 2>&1 & echo $!' % {"workflow_dir": self.workflow_dir,
                                            "topology_name": (
                                                self.storm_topology_name)})

        # Check result here
        self.assertEqual(("%s@%s" % (self.storm_topology_name,
                                     self.master_inst),
                          edp.JOB_STATUS_RUNNING,
                          {"storm-path": self.workflow_dir}), status)
