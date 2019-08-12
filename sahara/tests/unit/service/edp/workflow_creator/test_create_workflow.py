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

import testtools

import sahara.exceptions as ex
from sahara.service.edp.oozie.workflow_creator import hive_workflow as hw
from sahara.service.edp.oozie.workflow_creator import java_workflow as jw
from sahara.service.edp.oozie.workflow_creator import mapreduce_workflow as mrw
from sahara.service.edp.oozie.workflow_creator import pig_workflow as pw
from sahara.service.edp.oozie.workflow_creator import shell_workflow as shw


class TestWorkflowCreators(testtools.TestCase):

    def setUp(self):
        super(TestWorkflowCreators, self).setUp()
        self.prepare = {'delete': ['delete_dir_1', 'delete_dir_2'],
                        'mkdir': ['mkdir_1']}
        self.job_xml = 'job_xml.xml'
        self.configuration = {'conf_param_1': 'conf_value_1',
                              'conf_param_2': 'conf_value_3'}
        self.files = ['file1', 'file2']
        self.archives = ['arch1']
        self.streaming = {'mapper': '/usr/bin/cat',
                          'reducer': '/usr/bin/wc'}

    def test_create_mapreduce_streaming(self):
        mr_action = """
      <streaming>
        <mapper>/usr/bin/cat</mapper>
        <reducer>/usr/bin/wc</reducer>
      </streaming>"""

        mr_workflow = mrw.MapReduceWorkFlowCreator()
        mr_workflow.build_workflow_xml(self.prepare, self.job_xml,
                                       self.configuration, self.files,
                                       self.archives, self.streaming)
        res = mr_workflow.get_built_workflow_xml()
        self.assertIn(mr_action, res)

        mr_workflow = mrw.MapReduceWorkFlowCreator()
        mr_workflow.build_workflow_xml(self.prepare, self.job_xml,
                                       self.configuration, self.files,
                                       self.archives)
        res = mr_workflow.get_built_workflow_xml()
        self.assertNotIn(mr_action, res)

        mr_workflow = mrw.MapReduceWorkFlowCreator()
        with testtools.ExpectedException(ex.NotFoundException):
            mr_workflow.build_workflow_xml(self.prepare, self.job_xml,
                                           self.configuration, self.files,
                                           self.archives, {'bogus': 'element'})

    def test_create_mapreduce_workflow(self):
        mr_workflow = mrw.MapReduceWorkFlowCreator()
        mr_workflow.build_workflow_xml(self.prepare, self.job_xml,
                                       self.configuration, self.files,
                                       self.archives)
        res = mr_workflow.get_built_workflow_xml()
        mr_action = """    <map-reduce>
      <job-tracker>${jobTracker}</job-tracker>
      <name-node>${nameNode}</name-node>
      <prepare>
        <delete path="delete_dir_1"/>
        <delete path="delete_dir_2"/>
        <mkdir path="mkdir_1"/>
      </prepare>
      <job-xml>job_xml.xml</job-xml>
      <configuration>
        <property>
          <name>conf_param_1</name>
          <value>conf_value_1</value>
        </property>
        <property>
          <name>conf_param_2</name>
          <value>conf_value_3</value>
        </property>
      </configuration>
      <file>file1</file>
      <file>file2</file>
      <archive>arch1</archive>
    </map-reduce>"""

        self.assertIn(mr_action, res)

    def test_create_pig_workflow(self):
        pig_workflow = pw.PigWorkflowCreator()

        pig_script = 'script.pig'
        param_dict = {'param1': 'param_value1'}
        args = ['arg_value1', 'arg_value2']

        pig_workflow.build_workflow_xml(pig_script, self.prepare,
                                        self.job_xml, self.configuration,
                                        param_dict, args,
                                        self.files, self.archives)
        res = pig_workflow.get_built_workflow_xml()
        pig_action = """    <pig>
      <job-tracker>${jobTracker}</job-tracker>
      <name-node>${nameNode}</name-node>
      <prepare>
        <delete path="delete_dir_1"/>
        <delete path="delete_dir_2"/>
        <mkdir path="mkdir_1"/>
      </prepare>
      <job-xml>job_xml.xml</job-xml>
      <configuration>
        <property>
          <name>conf_param_1</name>
          <value>conf_value_1</value>
        </property>
        <property>
          <name>conf_param_2</name>
          <value>conf_value_3</value>
        </property>
      </configuration>
      <script>script.pig</script>
      <param>param1=param_value1</param>
      <argument>arg_value1</argument>
      <argument>arg_value2</argument>
      <file>file1</file>
      <file>file2</file>
      <archive>arch1</archive>
    </pig>"""

        self.assertIn(pig_action, res)

    def test_create_hive_workflow(self):
        hive_workflow = hw.HiveWorkflowCreator()
        hive_script = "script.q"
        params = {"key": "value", "key2": "value2"}
        hive_workflow.build_workflow_xml(hive_script, self.job_xml,
                                         self.prepare, self.configuration,
                                         params, self.files, self.archives)
        res = hive_workflow.get_built_workflow_xml()
        hive_action = """  <hive xmlns="uri:oozie:hive-action:0.2">
      <job-tracker>${jobTracker}</job-tracker>
      <name-node>${nameNode}</name-node>
      <prepare>
        <delete path="delete_dir_1"/>
        <delete path="delete_dir_2"/>
        <mkdir path="mkdir_1"/>
      </prepare>
      <job-xml>job_xml.xml</job-xml>
      <configuration>
        <property>
          <name>conf_param_1</name>
          <value>conf_value_1</value>
        </property>
        <property>
          <name>conf_param_2</name>
          <value>conf_value_3</value>
        </property>
      </configuration>
      <script>script.q</script>
      <param>key=value</param>
      <param>key2=value2</param>
      <file>file1</file>
      <file>file2</file>
      <archive>arch1</archive>
    </hive>"""

        self.assertIn(hive_action, res)

    def test_create_java_workflow(self):
        java_workflow = jw.JavaWorkflowCreator()
        main_class = 'org.apache.hadoop.examples.SomeClass'
        args = ['/user/hadoop/input',
                '/user/hadoop/output']
        java_opts = '-Dparam1=val1 -Dparam2=val2'

        java_workflow.build_workflow_xml(main_class,
                                         self.prepare,
                                         self.job_xml, self.configuration,
                                         java_opts, args,
                                         self.files, self.archives)
        res = java_workflow.get_built_workflow_xml()
        java_action = """
      <job-tracker>${jobTracker}</job-tracker>
      <name-node>${nameNode}</name-node>
      <prepare>
        <delete path="delete_dir_1"/>
        <delete path="delete_dir_2"/>
        <mkdir path="mkdir_1"/>
      </prepare>
      <job-xml>job_xml.xml</job-xml>
      <configuration>
        <property>
          <name>conf_param_1</name>
          <value>conf_value_1</value>
        </property>
        <property>
          <name>conf_param_2</name>
          <value>conf_value_3</value>
        </property>
      </configuration>
      <main-class>org.apache.hadoop.examples.SomeClass</main-class>
      <java-opts>-Dparam1=val1 -Dparam2=val2</java-opts>
      <arg>/user/hadoop/input</arg>
      <arg>/user/hadoop/output</arg>
      <file>file1</file>
      <file>file2</file>
      <archive>arch1</archive>
    </java>"""

        self.assertIn(java_action, res)

    def test_create_shell_workflow(self):
        shell_workflow = shw.ShellWorkflowCreator()
        main_class = 'doit.sh'
        args = ['now']
        env_vars = {"VERSION": 3}

        shell_workflow.build_workflow_xml(main_class,
                                          self.prepare,
                                          self.job_xml,
                                          self.configuration,
                                          env_vars,
                                          args,
                                          self.files)

        res = shell_workflow.get_built_workflow_xml()
        shell_action = """
    <shell xmlns="uri:oozie:shell-action:0.1">
      <job-tracker>${jobTracker}</job-tracker>
      <name-node>${nameNode}</name-node>
      <prepare>
        <delete path="delete_dir_1"/>
        <delete path="delete_dir_2"/>
        <mkdir path="mkdir_1"/>
      </prepare>
      <configuration>
        <property>
          <name>conf_param_1</name>
          <value>conf_value_1</value>
        </property>
        <property>
          <name>conf_param_2</name>
          <value>conf_value_3</value>
        </property>
      </configuration>
      <exec>doit.sh</exec>
      <argument>now</argument>
      <env-var>VERSION=3</env-var>
      <file>file1</file>
      <file>file2</file>
      <file>doit.sh</file>
    </shell>"""

        self.assertIn(shell_action, res)
