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

import re
import xml.dom.minidom as xml

import pkg_resources as pkg


# hadoop.xml related utils

def load_hadoop_xml_defaults(file_name, package='sahara'):
    doc = load_xml_document(file_name, package=package)
    configs = []
    prop = doc.getElementsByTagName('property')
    for elements in prop:
        configs.append({
            "name": get_text_from_node(elements, 'name'),
            "value": _adjust_field(get_text_from_node(elements, 'value')),
            "description": _adjust_field(
                get_text_from_node(elements, 'description'))
        })
    return configs


def parse_hadoop_xml_with_name_and_value(data):
    doc = xml.parseString(data)
    configs = []
    prop = doc.getElementsByTagName('property')
    for elements in prop:
        configs.append({
            'name': get_text_from_node(elements, 'name'),
            'value': get_text_from_node(elements, 'value')
        })

    return configs


def _get_node_element(element, name):
    element = element.getElementsByTagName(name)
    return element[0] if element and element[0].hasChildNodes() else None


def create_hadoop_xml(configs, config_filter=None):
    doc = xml.Document()

    pi = doc.createProcessingInstruction('xml-stylesheet',
                                         'type="text/xsl" '
                                         'href="configuration.xsl"')
    doc.insertBefore(pi, doc.firstChild)

    # Create the <configuration> base element
    configuration = doc.createElement('configuration')
    doc.appendChild(configuration)

    default_configs = []
    if config_filter is not None:
        default_configs = [cfg['name'] for cfg in config_filter]

    for name in sorted(configs):
        if name in default_configs or config_filter is None:
            add_property_to_configuration(doc, name, configs[name])

    # Return newly created XML
    return doc.toprettyxml(indent="  ")


def create_elements_xml(configs):
    doc = xml.Document()
    text = ''
    for name in sorted(configs):
        element = doc.createElement('property')
        add_text_element_to_element(doc, element, 'name', name)
        add_text_element_to_element(doc, element, 'value', configs[name])
        text += element.toprettyxml(indent="  ")
    return text


# basic utils

def load_xml_document(file_name, strip=False, package='sahara'):
    fname = pkg.resource_filename(package, file_name)
    if strip:
        with open(fname, "r") as f:
            doc = "".join(line.strip() for line in f)
            return xml.parseString(doc)
    else:
        return xml.parse(fname)


def get_text_from_node(element, name):
    element = element.getElementsByTagName(name) if element else None
    return element[0].firstChild.nodeValue if (
        element and element[0].hasChildNodes()) else ''


def _adjust_field(text):
    return re.sub(r"\n *|\t", "", str(text))


def add_property_to_configuration(doc, name, value):
    prop = add_child(doc, 'configuration', 'property')
    add_text_element_to_element(doc, prop, 'name', name)
    add_text_element_to_element(doc, prop, 'value', value)


def add_properties_to_configuration(doc, parent_for_conf, configs):
    get_and_create_if_not_exist(doc, parent_for_conf, 'configuration')
    for n in sorted(filter(lambda x: x, configs)):
        add_property_to_configuration(doc, n, configs[n])


def add_child(doc, parent, tag_to_add):
    actions = doc.getElementsByTagName(parent)
    actions[0].appendChild(doc.createElement(tag_to_add))
    return actions[0].lastChild


def add_element(doc, parent, element):
    actions = doc.getElementsByTagName(parent)
    actions[0].appendChild(element)
    return actions[0].lastChild


def get_and_create_if_not_exist(doc, parent, element):
    prop = doc.getElementsByTagName(element)
    if len(prop) != 0:
        return prop[0]
    return add_child(doc, parent, element)


def add_text_element_to_tag(doc, parent_tag, element, value):
    prop = add_child(doc, parent_tag, element)
    prop.appendChild(doc.createTextNode(str(value)))


def add_text_element_to_element(doc, parent, element, value):
    parent.appendChild(doc.createElement(element))
    try:
        parent.lastChild.appendChild(doc.createTextNode(str(value)))
    except UnicodeEncodeError:
        parent.lastChild.appendChild(doc.createTextNode(
            str(value.encode('utf8'))))


def add_equal_separated_dict(doc, parent_tag, each_elem_tag, value):
    for k in sorted(filter(lambda x: x, value)):
        if k:
            add_text_element_to_tag(doc, parent_tag, each_elem_tag,
                                    "%s=%s" % (k, value[k]))


def add_attributes_to_element(doc, tag, attributes):
    element = doc.getElementsByTagName(tag)[0]
    for name, value in attributes.items():
        element.setAttribute(name, value)


def add_tagged_list(doc, parent_tag, each_elem_tag, values):
    for v in values:
        add_text_element_to_tag(doc, parent_tag, each_elem_tag, v)


def get_property_dict(elem):
    res = {}
    properties = elem.getElementsByTagName('property')
    for prop in properties:
        k = get_text_from_node(prop, 'name')
        v = get_text_from_node(prop, 'value')
        res[k] = v
    return res


def get_param_dict(elem):
    res = {}
    params = elem.getElementsByTagName('param')
    for param in params:
        k, v = param.firstChild.nodeValue.split('=')
        res[k] = v
    return res
