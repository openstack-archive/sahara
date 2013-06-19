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

from savanna.utils import patches as p
from savanna.utils import xmlutils as x


class XMLUtilsTestCase(unittest2.TestCase):

    def setUp(self):
        p.patch_minidom_writexml()

    def test_load_xml_defaults(self):
        self.assertListEqual(
            [{'name': u'name1', 'value': u'value1', 'description': 'descr1'},
             {'name': u'name2', 'value': u'value2', 'description': 'descr2'},
             {'name': u'name3', 'value': '', 'description': 'descr3'},
             {'name': u'name4', 'value': '', 'description': 'descr4'},
             {'name': u'name5', 'value': u'value5', 'description': ''}],
            x.load_hadoop_xml_defaults(
                'tests/unit/resources/test-default.xml'))

    def test_adjust_description(self):
        self.assertEquals(x._adjust_description("\n"), "")
        self.assertEquals(x._adjust_description("\n  "), "")
        self.assertEquals(x._adjust_description(u"abc\n  def\n  "), "abcdef")
        self.assertEquals(x._adjust_description("abc d\n e f\n"), "abc de f")
        self.assertEquals(x._adjust_description("a\tb\t\nc"), "abc")

    def test_create_hadoop_xml(self):
        conf = x.load_hadoop_xml_defaults(
            'tests/unit/resources/test-default.xml')
        self.assertEquals(x.create_hadoop_xml({'name1': 'some_val1',
                                               'name2': 2}, conf),
                          """<?xml version="1.0" ?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
  <property>
    <name>name2</name>
    <value>2</value>
  </property>
  <property>
    <name>name1</name>
    <value>some_val1</value>
  </property>
</configuration>
""")
