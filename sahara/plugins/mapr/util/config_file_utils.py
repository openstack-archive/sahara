# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import six

import sahara.plugins.mapr.util.func_utils as fu
import sahara.utils.files as f
import sahara.utils.xmlutils as x


def load_properties_file(path):
    predicate = fu.and_predicate(lambda i: len(i) != 0,
                                 lambda i: not i.isspace(),
                                 lambda i: not i.startswith('#'))
    mapper = fu.chain_function(lambda i: tuple(i.split('=')),
                               lambda i: (i[0].strip(), i[1].strip()))
    lines = f.get_file_text(path).splitlines()
    return dict(map(mapper, filter(predicate, lines)))


def load_xml_file(path):
    kv_mapper = lambda i: (x.get_text_from_node(i, 'name'),
                           x._adjust_field(x.get_text_from_node(i, 'value')))
    strip_mapper = lambda i: (i[0].strip(), i[1].strip())
    props = x.load_xml_document(path).getElementsByTagName('property')
    return dict(map(strip_mapper, map(kv_mapper, props)))


def load_raw_file(path):
    return {'content': f.get_file_text(path)}


def to_properties_file_content(data):
    mapper = lambda i: '%s=%s\n' % i
    reducer = lambda p, c: p + c
    return reduce(reducer, map(mapper, six.iteritems(data)), '')


def to_xml_file_content(data):
    return x.create_hadoop_xml(data)


def to_topology_file_content(data):
    mapper = lambda i: '%s %s\n' % i
    reducer = lambda p, c: p + c
    return reduce(reducer, map(mapper, six.iteritems(data)))


def to_raw_file_content(data, cfu=True, conv=str):
    return data['content'] if cfu else conv(data)


def load_file(path, file_type):
    if file_type == 'properties':
        return load_properties_file(path)
    elif file_type == 'xml':
        return load_xml_file(path)
    elif file_type == 'raw':
        return load_raw_file(path)


def to_file_content(data, file_type, *args, **kargs):
    if file_type == 'properties':
        return to_properties_file_content(data, *args, **kargs)
    elif file_type == 'xml':
        return to_xml_file_content(data, *args, **kargs)
    elif file_type == 'topology':
        return to_topology_file_content(data, *args, **kargs)
    elif file_type == 'raw':
        return to_raw_file_content(data, *args, **kargs)
