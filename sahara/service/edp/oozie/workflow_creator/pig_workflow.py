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

from sahara.service.edp.oozie.workflow_creator import base_workflow
from sahara.utils import xmlutils as x


class PigWorkflowCreator(base_workflow.OozieWorkflowCreator):

    def __init__(self):
        super(PigWorkflowCreator, self).__init__('pig')

    def build_workflow_xml(self, script_name, prepare=None,
                           job_xml=None, configuration=None, params=None,
                           arguments=None, files=None, archives=None):

        prepare = prepare or {}
        params = params or {}
        arguments = arguments or []
        files = files or []
        archives = archives or []

        for k in sorted(prepare):
            self._add_to_prepare_element(k, prepare[k])

        self._add_job_xml_element(job_xml)
        self._add_configuration_elements(configuration)

        x.add_text_element_to_tag(self.doc, self.tag_name,
                                  'script', script_name)

        x.add_equal_separated_dict(self.doc, self.tag_name, 'param', params)

        for arg in arguments:
            x.add_text_element_to_tag(self.doc, self.tag_name, 'argument', arg)

        self._add_files_and_archives(files, archives)
