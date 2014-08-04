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

import copy

import mock
import testtools

from sahara import conductor as cond
from sahara import exceptions as ex
from sahara.plugins import base as pb
from sahara.service.edp import job_manager
from sahara.service.edp import job_utils
from sahara.service.edp.oozie import engine as oozie_engine
from sahara.service.edp.oozie.workflow_creator import workflow_factory
from sahara.swift import swift_helper as sw
from sahara.tests.unit import base
from sahara.utils import edp
from sahara.utils import patches as p


conductor = cond.API

_java_main_class = "org.apache.hadoop.examples.WordCount"
_java_opts = "-Dparam1=val1 -Dparam2=val2"


class TestJobManager(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestJobManager, self).setUp()
        p.patch_minidom_writexml()
        pb.setup_plugins()

    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.service.edp.hdfs_helper.create_dir')
    def test_create_job_dir(self, helper, remote):
        remote_class = mock.MagicMock()
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class
        helper.return_value = 'ok'

        job, _ = _create_all_stack(edp.JOB_TYPE_PIG)
        res = job_utils.create_hdfs_workflow_dir(mock.Mock(), job, 'hadoop')
        self.assertIn('/user/hadoop/special_name/', res)

        remote.reset_mock()
        remote_class.reset_mock()
        helper.reset_mock()

    @mock.patch('sahara.utils.remote.get_remote')
    @mock.patch('sahara.service.edp.hdfs_helper.put_file_to_hdfs')
    @mock.patch('sahara.service.edp.hdfs_helper._dir_missing')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper')
    @mock.patch('sahara.conductor.API.job_binary_internal_get_raw_data')
    def test_upload_job_files(self, conductor_raw_data, remote_class,
                              dir_missing, helper, remote):
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class
        helper.return_value = 'ok'
        dir_missing.return_value = False
        conductor_raw_data.return_value = 'ok'

        job, _ = _create_all_stack(edp.JOB_TYPE_PIG)
        res = job_utils.upload_job_files_to_hdfs(mock.Mock(), 'job_prefix',
                                                 job, 'hadoop')
        self.assertEqual(['job_prefix/script.pig'], res)

        job, _ = _create_all_stack(edp.JOB_TYPE_MAPREDUCE)
        res = job_utils.upload_job_files_to_hdfs(mock.Mock(), 'job_prefix',
                                                 job, 'hadoop')
        self.assertEqual(['job_prefix/lib/main.jar'], res)

        remote.reset_mock()
        remote_class.reset_mock()
        helper.reset_mock()

    def test_add_postfix(self):
        self.override_config("job_workflow_postfix", 'caba')
        res = job_utils._add_postfix('aba')
        self.assertEqual("aba/caba/", res)

        self.override_config("job_workflow_postfix", '')
        res = job_utils._add_postfix('aba')
        self.assertEqual("aba/", res)

    @mock.patch('sahara.conductor.API.job_binary_get')
    def test_build_workflow_for_job_pig(self, job_binary):

        job, job_exec = _create_all_stack(edp.JOB_TYPE_PIG)
        job_binary.return_value = {"name": "script.pig"}

        input_data = _create_data_source('swift://ex/i')
        output_data = _create_data_source('swift://ex/o')

        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec, input_data, output_data)

        self.assertIn("""
      <param>INPUT=swift://ex.sahara/i</param>
      <param>OUTPUT=swift://ex.sahara/o</param>""", res)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>admin</value>
        </property>
      </configuration>""", res)

        self.assertIn("<script>script.pig</script>", res)

    @mock.patch('sahara.conductor.API.job_binary_get')
    def test_build_workflow_swift_configs(self, job_binary):

        # Test that swift configs come from either input or output data sources
        job, job_exec = _create_all_stack(edp.JOB_TYPE_PIG)
        job_binary.return_value = {"name": "script.pig"}

        input_data = _create_data_source('swift://ex/i')
        output_data = _create_data_source('hdfs://user/hadoop/out')

        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec, input_data, output_data)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>admin</value>
        </property>
      </configuration>""", res)

        input_data = _create_data_source('hdfs://user/hadoop/in')
        output_data = _create_data_source('swift://ex/o')

        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec, input_data, output_data)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>admin</value>
        </property>
      </configuration>""", res)

        job, job_exec = _create_all_stack(
            edp.JOB_TYPE_PIG, configs={'configs': {'dummy': 'value'}})
        input_data = _create_data_source('hdfs://user/hadoop/in')
        output_data = _create_data_source('hdfs://user/hadoop/out')

        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec, input_data, output_data)

        self.assertIn("""
      <configuration>
        <property>
          <name>dummy</name>
          <value>value</value>
        </property>
      </configuration>""", res)

    def _build_workflow_common(self, job_type, streaming=False):
        if streaming:
            configs = {'edp.streaming.mapper': '/usr/bin/cat',
                       'edp.streaming.reducer': '/usr/bin/wc'}
            configs = {'configs': configs}
        else:
            configs = {}

        job, job_exec = _create_all_stack(job_type, configs)

        input_data = _create_data_source('swift://ex/i')
        output_data = _create_data_source('swift://ex/o')

        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec, input_data, output_data)

        if streaming:
            self.assertIn("""
      <streaming>
        <mapper>/usr/bin/cat</mapper>
        <reducer>/usr/bin/wc</reducer>
      </streaming>""", res)

        self.assertIn("""
        <property>
          <name>mapred.output.dir</name>
          <value>swift://ex.sahara/o</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>mapred.input.dir</name>
          <value>swift://ex.sahara/i</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>admin1</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>admin</value>
        </property>""", res)

    def test_build_workflow_for_job_mapreduce(self):
        self._build_workflow_common(edp.JOB_TYPE_MAPREDUCE)
        self._build_workflow_common(edp.JOB_TYPE_MAPREDUCE, streaming=True)

    def test_build_workflow_for_job_java(self):
        # If args include swift paths, user and password values
        # will have to be supplied via configs instead of being
        # lifted from input or output data sources
        configs = {sw.HADOOP_SWIFT_USERNAME: 'admin',
                   sw.HADOOP_SWIFT_PASSWORD: 'admin1'}

        configs = {
            'configs': configs,
            'args': ['swift://ex/i',
                     'output_path']
        }

        job, job_exec = _create_all_stack(edp.JOB_TYPE_JAVA, configs)
        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>admin</value>
        </property>
      </configuration>
      <main-class>%s</main-class>
      <java-opts>%s</java-opts>
      <arg>swift://ex.sahara/i</arg>
      <arg>output_path</arg>""" % (_java_main_class, _java_opts), res)

    @mock.patch('sahara.conductor.API.job_binary_get')
    def test_build_workflow_for_job_hive(self, job_binary):

        job, job_exec = _create_all_stack(edp.JOB_TYPE_HIVE)
        job_binary.return_value = {"name": "script.q"}

        input_data = _create_data_source('swift://ex/i')
        output_data = _create_data_source('swift://ex/o')

        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec, input_data, output_data)

        self.assertIn("""
      <job-xml>/user/hadoop/conf/hive-site.xml</job-xml>
      <configuration>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>admin</value>
        </property>
      </configuration>
      <script>script.q</script>
      <param>INPUT=swift://ex.sahara/i</param>
      <param>OUTPUT=swift://ex.sahara/o</param>""", res)

    def _build_workflow_with_conf_common(self, job_type):
        job, _ = _create_all_stack(job_type)

        input_data = _create_data_source('swift://ex/i')
        output_data = _create_data_source('swift://ex/o')

        job_exec = _create_job_exec(job.id,
                                    job_type, configs={"configs": {'c': 'f'}})

        res = workflow_factory.get_workflow_xml(
            job, _create_cluster(), job_exec, input_data, output_data)

        self.assertIn("""
        <property>
          <name>c</name>
          <value>f</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>mapred.input.dir</name>
          <value>swift://ex.sahara/i</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>mapred.output.dir</name>
          <value>swift://ex.sahara/o</value>
        </property>""", res)

    def test_build_workflow_for_job_mapreduce_with_conf(self):
        self._build_workflow_with_conf_common(edp.JOB_TYPE_MAPREDUCE)

    def test_update_job_dict(self):
        w = workflow_factory.BaseFactory()

        job_dict = {'configs': {'default1': 'value1',
                                'default2': 'value2'},
                    'params': {'param1': 'value1',
                               'param2': 'value2'},
                    'args': ['replace this', 'and this']}

        edp_configs = {'edp.streaming.mapper': '/usr/bin/cat',
                       'edp.streaming.reducer': '/usr/bin/wc'}
        configs = {'default2': 'changed'}
        configs.update(edp_configs)

        params = {'param1': 'changed'}

        exec_job_dict = {'configs': configs,
                         'params': params,
                         'args': ['replaced']}

        orig_exec_job_dict = copy.deepcopy(exec_job_dict)
        w.update_job_dict(job_dict, exec_job_dict)
        self.assertEqual(job_dict,
                         {'edp_configs': edp_configs,
                          'configs': {'default1': 'value1',
                                      'default2': 'changed'},
                          'params': {'param1': 'changed',
                                     'param2': 'value2'},
                          'args': ['replaced']})

        self.assertEqual(orig_exec_job_dict, exec_job_dict)

    def test_inject_swift_url_suffix(self):
        w = workflow_factory.BaseFactory()
        self.assertEqual(w.inject_swift_url_suffix("swift://ex/o"),
                         "swift://ex.sahara/o")
        self.assertEqual(w.inject_swift_url_suffix("swift://ex.sahara/o"),
                         "swift://ex.sahara/o")
        self.assertEqual(w.inject_swift_url_suffix("hdfs://my/path"),
                         "hdfs://my/path")

    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.service.edp.job_manager._run_job')
    def test_run_job_handles_exceptions(self, runjob, job_ex_upd):
        runjob.side_effect = ex.SwiftClientException("Unauthorised")
        job, job_exec = _create_all_stack(edp.JOB_TYPE_PIG)
        job_manager.run_job(job_exec.id)

        self.assertEqual(1, job_ex_upd.call_count)

        new_status = job_ex_upd.call_args[0][2]["info"]["status"]
        self.assertEqual(edp.JOB_STATUS_FAILED, new_status)

    def test_get_plugin(self):
        plugin = job_utils.get_plugin(_create_cluster())
        self.assertEqual("vanilla", plugin.name)

    @mock.patch('sahara.conductor.API.job_get')
    def test_job_type_supported(self, job_get):
        job, job_exec = _create_all_stack(edp.JOB_TYPE_PIG)
        job_get.return_value = job
        self.assertIsNotNone(job_manager._get_job_engine(_create_cluster(),
                                                         job_exec))

        job.type = "unsupported_type"
        self.assertIsNone(job_manager._get_job_engine(_create_cluster(),
                                                      job_exec))

    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.conductor.API.cluster_get')
    def test_run_job_unsupported_type(self,
                                      cluster_get, job_exec_get, job_get):
        job, job_exec = _create_all_stack("unsupported_type")
        job_exec_get.return_value = job_exec
        job_get.return_value = job

        cluster = _create_cluster()
        cluster.status = "Active"
        cluster_get.return_value = cluster
        with testtools.ExpectedException(ex.EDPError):
            job_manager._run_job(job_exec.id)

    @mock.patch('sahara.conductor.API.data_source_get')
    def test_get_data_sources(self, ds):
        job, job_exec = _create_all_stack(edp.JOB_TYPE_PIG)

        job_exec.input_id = 's1'
        job_exec.output_id = 's2'

        ds.side_effect = _conductor_data_source_get
        input_source, output_source = (
            job_utils.get_data_sources(job_exec, job))

        self.assertEqual('obj_s1', input_source)
        self.assertEqual('obj_s2', output_source)

    def test_get_data_sources_java(self):
        configs = {sw.HADOOP_SWIFT_USERNAME: 'admin',
                   sw.HADOOP_SWIFT_PASSWORD: 'admin1'}

        configs = {
            'configs': configs,
            'args': ['swift://ex/i',
                     'output_path']
        }

        job, job_exec = _create_all_stack(edp.JOB_TYPE_JAVA, configs)

        input_source, output_source = (
            job_utils.get_data_sources(job_exec, job))

        self.assertEqual(None, input_source)
        self.assertEqual(None, output_source)

    @mock.patch('sahara.service.edp.job_utils.get_plugin')
    def test_get_oozie_job_params(self, getplugin):
        plugin = mock.Mock()
        getplugin.return_value = plugin

        plugin.get_resource_manager_uri.return_value = 'http://localhost:50030'
        plugin.get_name_node_uri.return_value = 'hdfs://localhost:8020'

        cluster = _create_cluster()
        oje = oozie_engine.OozieJobEngine(cluster)
        job_params = oje._get_oozie_job_params('hadoop', '/tmp')
        self.assertEqual('http://localhost:50030', job_params["jobTracker"])
        self.assertEqual('hdfs://localhost:8020', job_params["nameNode"])
        self.assertEqual('hadoop', job_params["user.name"])


def _create_all_stack(type, configs=None):
    b = _create_job_binary('1', type)
    j = _create_job('2', b, type)
    e = _create_job_exec(j.id, type, configs)
    return j, e


def _create_job(id, job_binary, type):
    job = mock.Mock()
    job.id = id
    job.type = type
    job.name = 'special_name'
    if edp.compare_job_type(type, edp.JOB_TYPE_PIG, edp.JOB_TYPE_HIVE):
        job.mains = [job_binary]
        job.libs = None
    else:
        job.libs = [job_binary]
        job.mains = None
    return job


def _create_job_binary(id, type):
    binary = mock.Mock()
    binary.id = id
    binary.url = "internal-db://42"
    if edp.compare_job_type(type, edp.JOB_TYPE_PIG):
        binary.name = "script.pig"
    elif edp.compare_job_type(type, edp.JOB_TYPE_MAPREDUCE, edp.JOB_TYPE_JAVA):
        binary.name = "main.jar"
    else:
        binary.name = "script.q"
    return binary


def _create_cluster(plugin_name='vanilla', plugin_version='1.2.1'):
    cluster = mock.Mock()
    cluster.plugin_name = plugin_name
    cluster.plugin_version = plugin_version
    return cluster


def _create_data_source(url):
    data_source = mock.Mock()
    data_source.url = url
    if url.startswith("swift"):
        data_source.type = "swift"
        data_source.credentials = {'user': 'admin',
                                   'password': 'admin1'}
    elif url.startswith("hdfs"):
        data_source.type = "hdfs"
    return data_source


def _create_job_exec(job_id, type, configs=None):
    j_exec = mock.Mock()
    j_exec.job_id = job_id
    j_exec.job_configs = configs
    if edp.compare_job_type(type, edp.JOB_TYPE_JAVA):
        j_exec.job_configs['configs']['edp.java.main_class'] = _java_main_class
        j_exec.job_configs['configs']['edp.java.java_opts'] = _java_opts
    return j_exec


def _conductor_data_source_get(ctx, id):
    return "obj_" + id
