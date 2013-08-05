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

import unittest2

from savanna.service.edp.workflow_creator import pig_workflow as pw
from savanna.utils import patches as p


class TestPigWorkflowCreator(unittest2.TestCase):

    def setUp(self):
        p.patch_minidom_writexml()

    def test_create(self):
        pig_workflow = pw.PigWorkflowCreator()
        prepare_dict = {'delete': ['delete_dir_1',
                        'delete_dir_2'], 'mkdir': ['mkdir_1']}
        config_dict = {'conf_param_1': 'conf_value_1',
                       'conf_param_2': 'conf_value_3'}
        param_dict = {'param1': 'param_value1'}
        arg_dict = {'arg1': 'arg_value1', 'arg2': 'arg_value2'}
        file_list = ['file1', 'file2']
        archive_list = ['arch1']

        pig_workflow.build_workflow_xml('tracker_host', 'nn_host',
                                        'script.pig', prepare_dict,
                                        'job_xml.xml', config_dict,
                                        param_dict, arg_dict,
                                        file_list, archive_list)
        res = pig_workflow.get_built_workflow_xml()

        pig_action = """    <pig>
      <job-tracker>tracker_host</job-tracker>
      <name-node>nn_host</name-node>
      <script>script.pig</script>
      <prepare>
        <mkdir path="mkdir_1"/>
        <delete path="delete_dir_1"/>
        <delete path="delete_dir_2"/>
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
      <job-xml>job_xml.xml</job-xml>
      <param>param1=param_value1</param>
      <argument>arg1=arg_value1</argument>
      <argument>arg2=arg_value2</argument>
      <file>file1</file>
      <file>file2</file>
      <archive>arch1</archive>
    </pig>"""

        self.assertIn(pig_action, res)
