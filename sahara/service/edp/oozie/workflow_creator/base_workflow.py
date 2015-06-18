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


import xml.dom.minidom as xml

import sahara.exceptions as ex
from sahara.i18n import _
from sahara.utils import xmlutils as x


class OozieWorkflowCreator(object):

    doc = None
    tag_name = "no-op"

    def __init__(self, name):
        self.doc = x.load_xml_document("service/edp/resources/workflow.xml",
                                       strip=True)
        self.tag_name = name

        x.add_child(self.doc, 'action', self.tag_name)

        ok_elem = xml.parseString('<%s to="%s"/>' % ("ok", "end"))
        x.add_element(self.doc, 'action', ok_elem.firstChild)
        error_elem = xml.parseString('<%s to="%s"/>' % ("error", "fail"))
        x.add_element(self.doc, 'action', error_elem.firstChild)

        x.add_text_element_to_tag(self.doc, self.tag_name,
                                  'job-tracker', "${jobTracker}")
        x.add_text_element_to_tag(self.doc, self.tag_name,
                                  'name-node', "${nameNode}")

    def _add_to_prepare_element(self, element, paths):
        if element not in ['delete', 'mkdir']:
            raise ex.NotFoundException(element,
                                       _('"%s" child cannot be '
                                         'added to prepare element'))
        prop = x.get_and_create_if_not_exist(self.doc, self.tag_name,
                                             'prepare')
        for path in paths:
            elem = xml.parseString('<%s path="%s"/>' % (element, path))
            prop.appendChild(elem.firstChild)

    def _add_to_streaming_element(self, element, path):
        if element not in ['mapper', 'reducer']:
            raise ex.NotFoundException(element,
                                       _('"%s" child cannot be added '
                                         'to streaming element'))

        x.get_and_create_if_not_exist(self.doc, self.tag_name,
                                      'streaming')

        x.add_text_element_to_tag(self.doc, 'streaming', element, path)

    def _add_configuration_elements(self, configuration):
        if configuration:
            x.add_properties_to_configuration(self.doc, self.tag_name,
                                              configuration)

    def _add_job_xml_element(self, job_xml):
        if job_xml:
            x.add_text_element_to_tag(self.doc, self.tag_name,
                                      'job-xml', job_xml)

    def _add_files_and_archives(self, files, archives):
        if files:
            x.add_tagged_list(self.doc, self.tag_name, 'file', files)
        if archives:
            x.add_tagged_list(self.doc, self.tag_name, 'archive', archives)

    def get_built_workflow_xml(self):
        return self.doc.toprettyxml(indent="  ")
