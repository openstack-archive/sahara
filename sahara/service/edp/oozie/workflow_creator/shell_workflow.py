# Copyright (c) 2015 Red Hat Inc.
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


class ShellWorkflowCreator(base_workflow.OozieWorkflowCreator):

    SHELL_XMLNS = {"xmlns": "uri:oozie:shell-action:0.1"}

    def __init__(self):
        super(ShellWorkflowCreator, self).__init__('shell')

    def build_workflow_xml(self, script_name, prepare=None,
                           job_xml=None, configuration=None, env_vars=None,
                           arguments=None, files=None):
        x.add_attributes_to_element(self.doc, self.tag_name, self.SHELL_XMLNS)

        prepare = prepare or {}
        env_vars = env_vars or {}
        arguments = arguments or []
        files = files or []

        for k in sorted(prepare):
            self._add_to_prepare_element(k, prepare[k])

        self._add_configuration_elements(configuration)

        x.add_text_element_to_tag(self.doc, self.tag_name, 'exec', script_name)

        for arg in arguments:
            x.add_text_element_to_tag(self.doc, self.tag_name, 'argument', arg)

        x.add_equal_separated_dict(self.doc, self.tag_name,
                                   'env-var', env_vars)

        self._add_files_and_archives(files + [script_name], [])
