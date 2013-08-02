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

from savanna.service.edp.workflow_creator import base_workflow
from savanna.utils import xmlutils as x


class PigWorkflowCreator(base_workflow.OozieWorkflowCreator):

    def __init__(self):
        super(PigWorkflowCreator, self).__init__('pig')

    possible_dicts = ['prepare', 'param', 'argument', 'configuration']
    possible_lists = ['file', 'archive']
    possible_one_value_elems = ['job_xml', 'job_tracker',
                                'name_node', 'script']

    def get_possible_keys(self):
        return self.possible_lists + \
            self.possible_one_value_elems + self.possible_dicts

    def build_workflow_xml(self, job_tracker, name_node, script, prepare={},
                           job_xml=None, configuration=None, params={},
                           arguments={}, files=[], archives=[]):
        x.add_child(self.doc, 'action', 'pig')

        x.add_text_element_to_tag(self.doc, self.tag_name,
                                  'job-tracker', job_tracker)
        x.add_text_element_to_tag(self.doc, self.tag_name,
                                  'name-node', name_node)
        x.add_text_element_to_tag(self.doc, self.tag_name,
                                  'script', script)

        for k, v in prepare.items():
            self.add_to_prepare_element(k, v)

        if configuration:
            x.add_properties_to_configuration(self.doc, self.tag_name,
                                              configuration)
        if job_xml:
            x.add_text_element_to_tag(self.doc, self.tag_name,
                                      'job-xml', job_xml)

        x.add_equal_separated_dict(self.doc, self.tag_name, 'param', params)
        x.add_equal_separated_dict(self.doc, self.tag_name, 'argument',
                                   arguments)
        x.add_tagged_list(self.doc, self.tag_name, 'file', files)
        x.add_tagged_list(self.doc, self.tag_name, 'archive', archives)
