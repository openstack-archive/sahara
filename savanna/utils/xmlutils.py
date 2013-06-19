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

import pkg_resources as pkg
import re
import xml.dom.minidom as xml

from savanna import version


def load_xml_document(file_name):
    return xml.parse(pkg.resource_filename(
        version.version_info.package, file_name))


def load_hadoop_xml_defaults(file_name):
    doc = load_xml_document(file_name)
    configs = []
    prop = doc.getElementsByTagName('property')
    for elements in prop:
        configs.append({
            "name": _get_text_from_node(elements, 'name'),
            "value": _get_text_from_node(elements, 'value'),
            "description": _adjust_description(
                _get_text_from_node(elements, 'description'))
        })
    return configs


def _get_text_from_node(element, name):
    element = element.getElementsByTagName(name)
    return element[0].firstChild.nodeValue if (
        element and element[0].hasChildNodes()) else ''


def _adjust_description(text):
    return re.sub(r"\n *|\t", "", str(text))


def create_hadoop_xml(configs, global_conf):
    doc = xml.Document()

    pi = doc.createProcessingInstruction('xml-stylesheet',
                                         'type="text/xsl" '
                                         'href="configuration.xsl"')
    doc.insertBefore(pi, doc.firstChild)

    # Create the <configuration> base element
    configuration = doc.createElement("configuration")
    doc.appendChild(configuration)

    for name, value in configs.items():
        if name in [cfg['name'] for cfg in global_conf]:
            # Create the <property> element
            xml_prop = doc.createElement("property")
            configuration.appendChild(xml_prop)

            # Create a <name> element in <property>
            name_element = doc.createElement("name")
            xml_prop.appendChild(name_element)

            # Give the <name> element some hadoop config name
            name_text = doc.createTextNode(str(name))
            name_element.appendChild(name_text)

            # Create a <value> element in <property>
            value_element = doc.createElement("value")
            xml_prop.appendChild(value_element)

            # Give the <value> element some hadoop config value
            value_text = doc.createTextNode(str(value))
            value_element.appendChild(value_text)

    # Return newly created XML
    return doc.toprettyxml(indent="  ")
