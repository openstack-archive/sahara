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
from unittest import mock
import xml.dom.minidom as xml

import testtools

from sahara import conductor as cond
from sahara import exceptions as ex
from sahara.plugins import base as pb
from sahara.service.castellan import config as castellan
from sahara.service.edp import job_manager
from sahara.service.edp import job_utils
from sahara.service.edp.job_utils import ds_manager
from sahara.service.edp.oozie.workflow_creator import workflow_factory
from sahara.swift import swift_helper as sw
from sahara.swift import utils as su
from sahara.tests.unit import base
from sahara.tests.unit.service.edp import edp_test_utils as u
from sahara.utils import cluster as c_u
from sahara.utils import edp
from sahara.utils import xmlutils

conductor = cond.API

_java_main_class = "org.apache.hadoop.examples.WordCount"
_java_opts = "-Dparam1=val1 -Dparam2=val2"


class TestJobManager(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestJobManager, self).setUp()
        self.override_config('plugins', ['fake'])
        pb.setup_plugins()
        castellan.validate_config()
        ds_manager.setup_data_sources()

    @mock.patch('uuid.uuid4')
    @mock.patch('sahara.utils.remote.get_remote')
    def test_create_workflow_dir(self, get_remote, uuid4):
        job = mock.Mock()
        job.name = "job"

        # This is to mock "with remote.get_remote(instance) as r"
        remote_instance = mock.Mock()
        get_remote.return_value.__enter__ = mock.Mock(
            return_value=remote_instance)
        remote_instance.execute_command = mock.Mock()
        remote_instance.execute_command.return_value = 0, "standard out"

        uuid4.return_value = "generated_uuid"
        job_utils.create_workflow_dir("where", "/tmp/somewhere", job, "uuid")
        remote_instance.execute_command.assert_called_with(
            "mkdir -p /tmp/somewhere/job/uuid")
        remote_instance.execute_command.reset_mock()

        job_utils.create_workflow_dir("where", "/tmp/somewhere", job)
        remote_instance.execute_command.assert_called_with(
            "mkdir -p /tmp/somewhere/job/generated_uuid")

    @mock.patch('sahara.conductor.API.job_binary_get')
    def test_build_workflow_for_job_pig(self, job_binary):

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG, configs={})
        job_binary.return_value = {"name": "script.pig"}

        input_data = u.create_data_source('swift://ex/i')
        output_data = u.create_data_source('swift://ex/o')
        data_source_urls = {input_data.id: input_data.url,
                            output_data.id: output_data.url}

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

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

        # testing workflow creation with a proxy domain
        self.override_config('use_domain_for_proxy_users', True)
        self.override_config("proxy_user_domain_name", 'sahara_proxy_domain')
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG, proxy=True)

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.sahara.domain.name</name>
          <value>sahara_proxy_domain</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>55555555-6666-7777-8888-999999999999</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.trust.id</name>
          <value>0123456789abcdef0123456789abcdef</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>job_00000000-1111-2222-3333-4444444444444444</value>
        </property>
      </configuration>""", res)

    @mock.patch('sahara.conductor.API.job_binary_get')
    def test_build_workflow_swift_configs(self, job_binary):

        # Test that swift configs come from either input or output data sources
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG, configs={})
        job_binary.return_value = {"name": "script.pig"}

        input_data = u.create_data_source('swift://ex/i')
        output_data = u.create_data_source('hdfs://user/hadoop/out')
        data_source_urls = {input_data.id: input_data.url,
                            output_data.id: output_data.url}

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

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

        input_data = u.create_data_source('hdfs://user/hadoop/in')
        output_data = u.create_data_source('swift://ex/o')
        data_source_urls = {input_data.id: input_data.url,
                            output_data.id: output_data.url}

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

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

        job, job_exec = u.create_job_exec(
            edp.JOB_TYPE_PIG, configs={'configs': {'dummy': 'value'}})
        input_data = u.create_data_source('hdfs://user/hadoop/in')
        output_data = u.create_data_source('hdfs://user/hadoop/out')
        data_source_urls = {input_data.id: input_data.url,
                            output_data.id: output_data.url}

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

        self.assertIn("""
      <configuration>
        <property>
          <name>dummy</name>
          <value>value</value>
        </property>
      </configuration>""", res)

    def _build_workflow_common(self, job_type, streaming=False, proxy=False):
        if streaming:
            configs = {'edp.streaming.mapper': '/usr/bin/cat',
                       'edp.streaming.reducer': '/usr/bin/wc'}
            configs = {'configs': configs}
        else:
            configs = {}

        job, job_exec = u.create_job_exec(job_type, configs)

        input_data = u.create_data_source('swift://ex/i')
        output_data = u.create_data_source('swift://ex/o')
        data_source_urls = {input_data.id: input_data.url,
                            output_data.id: output_data.url}

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

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

        if not proxy:
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
        else:
            # testing workflow creation with a proxy domain
            self.override_config('use_domain_for_proxy_users', True)
            self.override_config("proxy_user_domain_name",
                                 'sahara_proxy_domain')
            job, job_exec = u.create_job_exec(job_type, proxy=True)

            res = workflow_factory.get_workflow_xml(
                job, u.create_cluster(), job_exec.job_configs,
                input_data, output_data, 'hadoop', data_source_urls)

            self.assertIn("""
        <property>
          <name>fs.swift.service.sahara.domain.name</name>
          <value>sahara_proxy_domain</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>55555555-6666-7777-8888-999999999999</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.trust.id</name>
          <value>0123456789abcdef0123456789abcdef</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>job_00000000-1111-2222-3333-4444444444444444</value>
        </property>""", res)

    def test_build_workflow_for_job_mapreduce(self):
        self._build_workflow_common(edp.JOB_TYPE_MAPREDUCE)
        self._build_workflow_common(edp.JOB_TYPE_MAPREDUCE, streaming=True)
        self._build_workflow_common(edp.JOB_TYPE_MAPREDUCE, proxy=True)
        self._build_workflow_common(edp.JOB_TYPE_MAPREDUCE, streaming=True,
                                    proxy=True)

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

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_JAVA, configs)
        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs)

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

        # testing workflow creation with a proxy domain
        self.override_config('use_domain_for_proxy_users', True)
        self.override_config("proxy_user_domain_name", 'sahara_proxy_domain')
        configs = {
            'configs': {},
            'args': ['swift://ex/i',
                     'output_path']
        }

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_JAVA, configs,
                                          proxy=True)
        res = workflow_factory.get_workflow_xml(job, u.create_cluster(),
                                                job_exec.job_configs)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.sahara.domain.name</name>
          <value>sahara_proxy_domain</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.password</name>
          <value>55555555-6666-7777-8888-999999999999</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.trust.id</name>
          <value>0123456789abcdef0123456789abcdef</value>
        </property>
        <property>
          <name>fs.swift.service.sahara.username</name>
          <value>job_00000000-1111-2222-3333-4444444444444444</value>
        </property>
      </configuration>
      <main-class>%s</main-class>
      <java-opts>%s</java-opts>
      <arg>swift://ex.sahara/i</arg>
      <arg>output_path</arg>""" % (_java_main_class, _java_opts), res)

    @mock.patch("sahara.service.edp.oozie.workflow_creator.workflow_factory."
                "edp.is_adapt_for_oozie_enabled")
    def test_build_workflow_for_job_java_with_adapter(self, edp_conf_mock):
        edp_conf_mock.return_value = True

        configs = {"configs": {"edp.java.main_class": "some_main"}}
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_JAVA, configs)
        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs)

        self.assertIn(
            "<main-class>org.openstack.sahara.edp.MainWrapper</main-class>",
            res)
        self.assertNotIn("some_main", res)

    @mock.patch('sahara.conductor.API.job_binary_get')
    def test_build_workflow_for_job_hive(self, job_binary):

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_HIVE, configs={})
        job_binary.return_value = {"name": "script.q"}

        input_data = u.create_data_source('swift://ex/i')
        output_data = u.create_data_source('swift://ex/o')
        data_source_urls = {input_data.id: input_data.url,
                            output_data.id: output_data.url}

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

        doc = xml.parseString(res)
        hive = doc.getElementsByTagName('hive')[0]
        self.assertEqual('/user/hadoop/conf/hive-site.xml',
                         xmlutils.get_text_from_node(hive, 'job-xml'))

        configuration = hive.getElementsByTagName('configuration')
        properties = xmlutils.get_property_dict(configuration[0])
        self.assertEqual({'fs.swift.service.sahara.password': 'admin1',
                          'fs.swift.service.sahara.username': 'admin'},
                         properties)

        self.assertEqual('script.q',
                         xmlutils.get_text_from_node(hive, 'script'))

        params = xmlutils.get_param_dict(hive)
        self.assertEqual({'INPUT': 'swift://ex.sahara/i',
                          'OUTPUT': 'swift://ex.sahara/o'}, params)

        # testing workflow creation with a proxy domain
        self.override_config('use_domain_for_proxy_users', True)
        self.override_config("proxy_user_domain_name", 'sahara_proxy_domain')

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_HIVE, proxy=True)

        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs,
            input_data, output_data, 'hadoop', data_source_urls)

        doc = xml.parseString(res)
        hive = doc.getElementsByTagName('hive')[0]
        configuration = hive.getElementsByTagName('configuration')
        properties = xmlutils.get_property_dict(configuration[0])
        self.assertEqual({
            'fs.swift.service.sahara.domain.name':
            'sahara_proxy_domain',

            'fs.swift.service.sahara.trust.id':
            '0123456789abcdef0123456789abcdef',

            'fs.swift.service.sahara.password':
            '55555555-6666-7777-8888-999999999999',

            'fs.swift.service.sahara.username':
            'job_00000000-1111-2222-3333-4444444444444444'}, properties)

    def test_build_workflow_for_job_shell(self):
        configs = {"configs": {"k1": "v1"},
                   "params": {"p1": "v1"},
                   "args": ["a1", "a2"]}
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_SHELL, configs)
        res = workflow_factory.get_workflow_xml(
            job, u.create_cluster(), job_exec.job_configs)

        self.assertIn("<name>k1</name>", res)
        self.assertIn("<value>v1</value>", res)

        self.assertIn("<env-var>p1=v1</env-var>", res)

        self.assertIn("<argument>a1</argument>", res)
        self.assertIn("<argument>a2</argument>", res)

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
        self.assertEqual({'edp_configs': edp_configs,
                          'configs': {'default1': 'value1',
                                      'default2': 'changed'},
                          'params': {'param1': 'changed',
                                     'param2': 'value2'},
                          'args': ['replaced']}, job_dict)

        self.assertEqual(orig_exec_job_dict, exec_job_dict)

    def test_inject_swift_url_suffix(self):
        self.assertEqual("swift://ex.sahara/o",
                         su.inject_swift_url_suffix("swift://ex/o"))
        self.assertEqual("swift://ex.sahara/o",
                         su.inject_swift_url_suffix("swift://ex.sahara/o"))
        self.assertEqual("hdfs://my/path",
                         su.inject_swift_url_suffix("hdfs://my/path"))
        self.assertEqual(12345, su.inject_swift_url_suffix(12345))
        self.assertEqual(['test'], su.inject_swift_url_suffix(['test']))

    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.service.edp.job_manager._run_job')
    @mock.patch('sahara.service.edp.job_manager.cancel_job')
    def test_run_job_handles_exceptions(self, canceljob, runjob,
                                        job_ex_get, job_ex_upd):
        runjob.side_effect = ex.SwiftClientException("Unauthorised")
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)

        job_exec.engine_job_id = None
        job_ex_get.return_value = job_exec

        job_manager.run_job(job_exec.id)

        self.assertEqual(1, job_ex_get.call_count)
        self.assertEqual(1, job_ex_upd.call_count)

        new_status = job_ex_upd.call_args[0][2]["info"]["status"]
        self.assertEqual(edp.JOB_STATUS_FAILED, new_status)
        self.assertEqual(0, canceljob.call_count)

    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.service.edp.job_manager._run_job')
    @mock.patch('sahara.service.edp.job_manager.cancel_job')
    def test_run_job_handles_exceptions_with_run_job(self, canceljob, runjob,
                                                     job_ex_get, job_ex_upd):
        runjob.side_effect = ex.OozieException("run_job failed")
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)
        job_exec.engine_job_id = "fake_oozie_id"
        job_ex_get.return_value = job_exec

        job_manager.run_job(job_exec.id)

        self.assertEqual(1, job_ex_get.call_count)
        self.assertEqual(1, job_ex_upd.call_count)

        new_status = job_ex_upd.call_args[0][2]["info"]["status"]
        self.assertEqual(edp.JOB_STATUS_FAILED, new_status)
        self.assertEqual(1, canceljob.call_count)

    def test_get_plugin(self):
        plugin = job_utils.get_plugin(u.create_cluster())
        self.assertEqual("fake", plugin.name)

    @mock.patch('sahara.conductor.API.job_get')
    def test_job_type_supported(self, job_get):
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)
        job_get.return_value = job
        self.assertIsNotNone(job_manager.get_job_engine(u.create_cluster(),
                                                        job_exec))

        job.type = "unsupported_type"
        self.assertIsNone(job_manager.get_job_engine(u.create_cluster(),
                                                     job_exec))

    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.conductor.API.cluster_get')
    def test_run_job_unsupported_type(self,
                                      cluster_get, job_exec_get, job_get):
        job, job_exec = u.create_job_exec("unsupported_type")
        job_exec_get.return_value = job_exec
        job_get.return_value = job

        cluster = u.create_cluster()
        cluster.status = c_u.CLUSTER_STATUS_ACTIVE
        cluster_get.return_value = cluster
        with testtools.ExpectedException(ex.EDPError):
            job_manager._run_job(job_exec.id)

    @mock.patch('sahara.conductor.API.data_source_get')
    def test_get_input_output_data_sources(self, ds):
        def _conductor_data_source_get(ctx, id):
            return mock.Mock(id=id, url="hdfs://obj_" + id, type='hdfs')

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG)

        job_exec.input_id = 's1'
        job_exec.output_id = 's2'

        ds.side_effect = _conductor_data_source_get
        input_source, output_source = (
            job_utils.get_input_output_data_sources(job_exec, job, {}))

        self.assertEqual('hdfs://obj_s1', input_source.url)
        self.assertEqual('hdfs://obj_s2', output_source.url)

    def test_get_input_output_data_sources_with_null_id(self):
        configs = {sw.HADOOP_SWIFT_USERNAME: 'admin',
                   sw.HADOOP_SWIFT_PASSWORD: 'admin1'}

        configs = {
            'configs': configs,
            'args': ['hdfs://ex/i',
                     'output_path']
        }

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_JAVA, configs)

        job_exec.input_id = None
        job_exec.output_id = None

        input_source, output_source = (
            job_utils.get_input_output_data_sources(job_exec, job, {}))

        self.assertIsNone(input_source)
        self.assertIsNone(output_source)

    @mock.patch('sahara.conductor.API.job_execution_update')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('oslo_utils.timeutils.delta_seconds')
    def test_failed_to_cancel_job(self, time_get, cluster_get, job_exec_get,
                                  job_get, job_execution_update_get):
        info = {
            'status': edp.JOB_STATUS_RUNNING
        }

        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG, None, False, info)
        job_exec_get.return_value = job_exec
        job_get.return_value = job

        cluster = u.create_cluster()
        cluster.status = c_u.CLUSTER_STATUS_ACTIVE
        cluster_get.return_value = cluster

        time_get.return_value = 10000

        job_execution_update_get.return_value = job_exec

        with testtools.ExpectedException(ex.CancelingFailed):
            job_manager.cancel_job(job_exec.id)

    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch(
        'sahara.service.edp.oozie.engine.OozieJobEngine.run_scheduled_job')
    def test_scheduled_edp_job_run(self, job_exec_get, cluster_get,
                                   job_get, run_scheduled_job):
        configs = {
            'job_execution_info': {
                'job_execution_type': 'scheduled',
                'start': '2015-5-15T01:00Z'
            }
        }
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG, configs)
        job_exec_get.return_value = job_exec
        job_get.return_value = job

        cluster = u.create_cluster()
        cluster.status = "Active"
        cluster_get.return_value = cluster

        job_manager._run_job(job_exec.id)

        self.assertEqual(1, run_scheduled_job.call_count)

    @mock.patch('sahara.conductor.API.job_get')
    @mock.patch('sahara.conductor.API.job_execution_get')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.service.edp.base_engine.JobEngine.suspend_job')
    def test_suspend_unsuspendible_job(self, suspend_job_get,
                                       cluster_get, job_exec_get, job_get):
        info = {
            'status': edp.JOB_STATUS_SUCCEEDED
        }
        job, job_exec = u.create_job_exec(edp.JOB_TYPE_PIG, None, False, info)
        job_exec_get.return_value = job_exec
        job_get.return_value = job

        cluster = u.create_cluster()
        cluster.status = "Active"
        cluster_get.return_value = cluster

        self.assertEqual(0, suspend_job_get.call_count)
