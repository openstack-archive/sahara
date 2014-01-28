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

from savanna import conductor as cond
from savanna.conductor import resource as r
from savanna.service.edp import job_manager
from savanna.service.edp.workflow_creator import workflow_factory
from savanna.tests.unit import base as models_test_base
from savanna.utils import patches as p


conductor = cond.API

_java_main_class = "org.apache.hadoop.examples.WordCount"
_java_opts = "-Dparam1=val1 -Dparam2=val2"


def _resource_passthrough(*args, **kwargs):
    return True


class TestJobManager(models_test_base.DbTestCase):
    def setUp(self):
        r.Resource._is_passthrough_type = _resource_passthrough
        p.patch_minidom_writexml()
        super(TestJobManager, self).setUp()

    @mock.patch('savanna.utils.remote.get_remote')
    @mock.patch('savanna.service.edp.hdfs_helper.create_dir')
    @mock.patch('savanna.utils.remote.InstanceInteropHelper')
    def test_create_job_dir(self, remote_class, helper, remote):
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class
        helper.return_value = 'ok'

        job, _ = _create_all_stack('Pig')
        res = job_manager.create_workflow_dir(mock.Mock(), job, 'hadoop')
        self.assertIn('/user/hadoop/special_name/', res)

        remote.reset_mock()
        remote_class.reset_mock()
        helper.reset_mock()

    @mock.patch('savanna.utils.remote.get_remote')
    @mock.patch('savanna.service.edp.hdfs_helper.put_file_to_hdfs')
    @mock.patch('savanna.utils.remote.InstanceInteropHelper')
    @mock.patch('savanna.conductor.API.job_binary_internal_get_raw_data')
    def test_upload_job_files(self, conductor_raw_data, remote_class,
                              helper, remote):
        remote_class.__exit__.return_value = 'closed'
        remote.return_value = remote_class
        helper.return_value = 'ok'
        conductor_raw_data.return_value = 'ok'

        job, _ = _create_all_stack('Pig')
        res = job_manager.upload_job_files(mock.Mock(), 'job_prefix',
                                           job, 'hadoop')
        self.assertEqual(['job_prefix/script.pig'], res)

        job, _ = _create_all_stack('MapReduce')
        res = job_manager.upload_job_files(mock.Mock(), 'job_prefix',
                                           job, 'hadoop')
        self.assertEqual(['job_prefix/lib/main.jar'], res)

        job, _ = _create_all_stack('Jar')
        res = job_manager.upload_job_files(mock.Mock(), 'job_prefix',
                                           job, 'hadoop')
        self.assertEqual(['job_prefix/lib/main.jar'], res)

        remote.reset_mock()
        remote_class.reset_mock()
        helper.reset_mock()

    @mock.patch('oslo.config.cfg.CONF.job_workflow_postfix')
    def test_add_postfix(self, conf):
        conf.__str__.return_value = 'caba'
        res = job_manager._add_postfix('aba')
        self.assertEqual("aba/caba/", res)

        conf.__str__.return_value = ''
        res = job_manager._add_postfix('aba')
        self.assertEqual("aba/", res)

        conf.reset_mock()

    @mock.patch('savanna.conductor.API.job_binary_get')
    def test_build_workflow_for_job_pig(self, job_binary):

        job, job_exec = _create_all_stack('Pig')
        job_binary.return_value = {"name": "script.pig"}

        input_data = _create_data_source('swift://ex.savanna/i')
        output_data = _create_data_source('swift://ex.savanna/o')

        creator = workflow_factory.get_creator(job)

        res = creator.get_workflow_xml(job_exec,
                                       input_data, output_data)

        self.assertIn("""
      <param>INPUT=swift://ex.savanna/i</param>
      <param>OUTPUT=swift://ex.savanna/o</param>""", res)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.savanna.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.savanna.username</name>
          <value>admin</value>
        </property>
      </configuration>""", res)

        self.assertIn("<script>script.pig</script>", res)

    @mock.patch('savanna.conductor.API.job_binary_get')
    def test_build_workflow_swift_configs(self, job_binary):

        # Test that swift configs come from either input or output data sources
        job, job_exec = _create_all_stack('Pig')
        job_binary.return_value = {"name": "script.pig"}

        input_data = _create_data_source('swift://ex.savanna/i')
        output_data = _create_data_source('hdfs://user/hadoop/out')

        creator = workflow_factory.get_creator(job)
        res = creator.get_workflow_xml(job_exec,
                                       input_data, output_data)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.savanna.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.savanna.username</name>
          <value>admin</value>
        </property>
      </configuration>""", res)

        input_data = _create_data_source('hdfs://user/hadoop/in')
        output_data = _create_data_source('swift://ex.savanna/o')

        creator = workflow_factory.get_creator(job)

        res = creator.get_workflow_xml(job_exec,
                                       input_data, output_data)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.savanna.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.savanna.username</name>
          <value>admin</value>
        </property>
      </configuration>""", res)

        job, job_exec = _create_all_stack('Pig', configs={'configs':
                                                          {'dummy': 'value'}})
        input_data = _create_data_source('hdfs://user/hadoop/in')
        output_data = _create_data_source('hdfs://user/hadoop/out')

        creator = workflow_factory.get_creator(job)

        res = creator.get_workflow_xml(job_exec,
                                       input_data, output_data)

        self.assertIn("""
      <configuration>
        <property>
          <name>dummy</name>
          <value>value</value>
        </property>
      </configuration>""", res)

    def _build_workflow_common(self, job_type):
        job, job_exec = _create_all_stack(job_type)

        input_data = _create_data_source('swift://ex.savanna/i')
        output_data = _create_data_source('swift://ex.savanna/o')

        creator = workflow_factory.get_creator(job)

        res = creator.get_workflow_xml(job_exec,
                                       input_data, output_data)

        self.assertIn("""
        <property>
          <name>mapred.output.dir</name>
          <value>swift://ex.savanna/o</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>mapred.input.dir</name>
          <value>swift://ex.savanna/i</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>fs.swift.service.savanna.password</name>
          <value>admin1</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>fs.swift.service.savanna.username</name>
          <value>admin</value>
        </property>""", res)

    def test_build_workflow_for_job_mapreduce(self):
        self._build_workflow_common('MapReduce')

    def test_build_workflow_for_job_jar(self):
        self._build_workflow_common('Jar')

    def test_build_workflow_for_job_java(self):
        # If args include swift paths, user and password values
        # will have to be supplied via configs instead of being
        # lifted from input or output data sources
        configs = {workflow_factory.swift_username: 'admin',
                   workflow_factory.swift_password: 'admin1'}

        configs = {
            'configs': configs,
            'args': ['input_path',
                     'output_path']
        }

        job, job_exec = _create_all_stack('Java', configs)
        creator = workflow_factory.get_creator(job)
        res = creator.get_workflow_xml(job_exec)

        self.assertIn("""
      <configuration>
        <property>
          <name>fs.swift.service.savanna.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.savanna.username</name>
          <value>admin</value>
        </property>
      </configuration>
      <main-class>%s</main-class>
      <java-opts>%s</java-opts>
      <arg>input_path</arg>
      <arg>output_path</arg>""" % (_java_main_class, _java_opts), res)

    @mock.patch('savanna.conductor.API.job_binary_get')
    def test_build_workflow_for_job_hive(self, job_binary):

        job, job_exec = _create_all_stack('Hive')
        job_binary.return_value = {"name": "script.q"}

        input_data = _create_data_source('swift://ex.savanna/i')
        output_data = _create_data_source('swift://ex.savanna/o')

        creator = workflow_factory.get_creator(job)

        res = creator.get_workflow_xml(job_exec,
                                       input_data, output_data)

        self.assertIn("""
      <job-xml>hive-site.xml</job-xml>
      <configuration>
        <property>
          <name>fs.swift.service.savanna.password</name>
          <value>admin1</value>
        </property>
        <property>
          <name>fs.swift.service.savanna.username</name>
          <value>admin</value>
        </property>
      </configuration>
      <script>script.q</script>
      <param>INPUT=swift://ex.savanna/i</param>
      <param>OUTPUT=swift://ex.savanna/o</param>""", res)

    def _build_workflow_with_conf_common(self, job_type):
        job, _ = _create_all_stack(job_type)

        input_data = _create_data_source('swift://ex.savanna/i')
        output_data = _create_data_source('swift://ex.savanna/o')

        job_exec = _create_job_exec(job.id,
                                    job_type, configs={"configs": {'c': 'f'}})

        creator = workflow_factory.get_creator(job)

        res = creator.get_workflow_xml(job_exec,
                                       input_data, output_data)

        self.assertIn("""
        <property>
          <name>c</name>
          <value>f</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>mapred.input.dir</name>
          <value>swift://ex.savanna/i</value>
        </property>""", res)

        self.assertIn("""
        <property>
          <name>mapred.output.dir</name>
          <value>swift://ex.savanna/o</value>
        </property>""", res)

    def test_build_workflow_for_job_mapreduce_with_conf(self):
        self._build_workflow_with_conf_common('MapReduce')

    def test_build_workflow_for_job_jar_with_conf(self):
        self._build_workflow_with_conf_common('Jar')

    def test_jar_creator_is_mapreduce(self):
        # Ensure that we get the MapReduce workflow factory for 'Jar' jobs
        job, _ = _create_all_stack('Jar')

        creator = workflow_factory.get_creator(job)
        self.assertEqual(type(creator), workflow_factory.MapReduceFactory)

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
                          'configs':  {'default1': 'value1',
                                       'default2': 'changed'},
                          'params': {'param1': 'changed',
                                     'param2': 'value2'},
                          'args': ['replaced']})

        self.assertEqual(orig_exec_job_dict, exec_job_dict)


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
    if type == 'Pig' or type == 'Hive':
        job.mains = [job_binary]
        job.libs = None
    if type in ['MapReduce', 'Jar', 'Java']:
        job.libs = [job_binary]
        job.mains = None
    return job


def _create_job_binary(id, type):
    binary = mock.Mock()
    binary.id = id
    binary.url = "savanna-db://42"
    if type == "Pig":
        binary.name = "script.pig"
    if type in ['MapReduce', 'Jar', 'Java']:
        binary.name = "main.jar"
    if type == "Hive":
        binary.name = "script.q"
    return binary


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
    if type == "Java":
        j_exec.main_class = _java_main_class
        j_exec.java_opts = _java_opts
    return j_exec
