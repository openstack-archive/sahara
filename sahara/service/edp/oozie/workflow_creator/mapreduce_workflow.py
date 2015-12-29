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


class MapReduceWorkFlowCreator(base_workflow.OozieWorkflowCreator):

    def __init__(self):
        super(MapReduceWorkFlowCreator, self).__init__('map-reduce')

    def build_workflow_xml(self, prepare=None,
                           job_xml=None, configuration=None,
                           files=None, archives=None,
                           streaming=None):

        prepare = prepare or {}
        files = files or []
        archives = archives or []
        streaming = streaming or {}

        for k in sorted(prepare):
            self._add_to_prepare_element(k, prepare[k])

        # TODO(aignatov): Need to add PIPES workflow

        for k in sorted(streaming):
            self._add_to_streaming_element(k, streaming[k])

        self._add_job_xml_element(job_xml)

        self._add_configuration_elements(configuration)

        self._add_files_and_archives(files, archives)
