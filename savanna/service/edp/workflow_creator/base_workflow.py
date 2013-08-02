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

import savanna.exceptions as ex
from savanna.utils import xmlutils as x


class OozieWorkflowCreator(object):

    doc = None
    tag_name = "empty"

    def __init__(self, name):
        self.doc = x.load_xml_document("service/edp/resources/workflow.xml")
        self.tag_name = name

    def add_to_prepare_element(self, element, paths):
        if element not in ['delete', 'mkdir']:
            raise ex.NotFoundException(element, message=
                                       '"%s" child cannot be added to '
                                       'prepare element')
        prop = x.get_and_create_if_not_exist(self.doc, self.tag_name,
                                             'prepare')
        for path in paths:
            elem = xml.parseString('<%s path="%s"/>' % (element, path))
            prop.appendChild(elem.firstChild)

    def get_built_workflow_xml(self):
        return self.doc.toprettyxml(indent="  ")
