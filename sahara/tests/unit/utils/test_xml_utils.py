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

import pkg_resources as pkg
import testtools

from sahara.utils import xmlutils as x
from sahara import version


class XMLUtilsTestCase(testtools.TestCase):

    def setUp(self):
        super(XMLUtilsTestCase, self).setUp()

    def test_load_xml_defaults(self):
        self.assertEqual(
            [{'name': 'name1', 'value': 'value1', 'description': 'descr1'},
             {'name': 'name2', 'value': 'value2', 'description': 'descr2'},
             {'name': 'name3', 'value': '', 'description': 'descr3'},
             {'name': 'name4', 'value': '', 'description': 'descr4'},
             {'name': 'name5', 'value': 'value5', 'description': ''}],
            x.load_hadoop_xml_defaults(
                'tests/unit/resources/test-default.xml'))

    def test_parse_xml_with_name_and_value(self):
        file_name = 'tests/unit/resources/test-default.xml'
        fname = pkg.resource_filename(
            version.version_info.package, file_name)
        with open(fname, "r") as f:
            doc = "".join(line.strip() for line in f)
        self.assertEqual(
            [{'name': 'name1', 'value': 'value1'},
             {'name': 'name2', 'value': 'value2'},
             {'name': 'name3', 'value': ''},
             {'name': 'name4', 'value': ''},
             {'name': 'name5', 'value': 'value5'}],
            x.parse_hadoop_xml_with_name_and_value(doc)
        )

    def test_adjust_description(self):
        self.assertEqual("", x._adjust_field("\n"))
        self.assertEqual("", x._adjust_field("\n  "))
        self.assertEqual("abcdef", x._adjust_field("abc\n  def\n  "))
        self.assertEqual("abc de f", x._adjust_field("abc d\n e f\n"))
        self.assertEqual("abc", x._adjust_field("a\tb\t\nc"))

    def test_create_hadoop_xml(self):
        conf = x.load_hadoop_xml_defaults(
            'tests/unit/resources/test-default.xml')
        self.assertEqual("""<?xml version="1.0" ?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
  <property>
    <name>name1</name>
    <value>some_val1</value>
  </property>
  <property>
    <name>name2</name>
    <value>2</value>
  </property>
</configuration>
""",
                         x.create_hadoop_xml({'name1': 'some_val1',
                                              'name2': 2}, conf),)

    def test_add_property_to_configuration(self):
        doc = self.create_default_doc()
        x.add_properties_to_configuration(doc, 'test', {'': 'empty1',
                                                        None: 'empty2'})
        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <configuration/>
</test>
""",
                         doc.toprettyxml(indent="  "))

        test_conf = {'name1': 'value1', 'name2': 'value2'}
        x.add_properties_to_configuration(doc, 'test', test_conf)

        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <configuration>
    <property>
      <name>name1</name>
      <value>value1</value>
    </property>
    <property>
      <name>name2</name>
      <value>value2</value>
    </property>
  </configuration>
</test>
""",
                         doc.toprettyxml(indent="  "))
        x.add_property_to_configuration(doc, 'name3', 'value3')
        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <configuration>
    <property>
      <name>name1</name>
      <value>value1</value>
    </property>
    <property>
      <name>name2</name>
      <value>value2</value>
    </property>
    <property>
      <name>name3</name>
      <value>value3</value>
    </property>
  </configuration>
</test>
""",
                         doc.toprettyxml(indent="  "))

    def test_get_if_not_exist_and_add_text_element(self):
        doc = self.create_default_doc()
        x.get_and_create_if_not_exist(doc, 'test', 'tag_to_add')
        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <tag_to_add/>
</test>
""",
                         doc.toprettyxml(indent="  "))
        x.add_text_element_to_tag(doc, 'tag_to_add', 'p', 'v')
        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <tag_to_add>
    <p>v</p>
  </tag_to_add>
</test>
""",
                         doc.toprettyxml(indent="  "))

    def test_get_if_not_exist_and_add_to_element(self):
        doc = self.create_default_doc()
        elem = x.get_and_create_if_not_exist(doc, 'test', 'tag_to_add')

        x.add_text_element_to_element(doc, elem, 'p', 'v')
        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <tag_to_add>
    <p>v</p>
  </tag_to_add>
</test>
""",
                         doc.toprettyxml(indent="  "))

    def test_add_tagged_list(self):
        doc = self.create_default_doc()
        x.add_tagged_list(doc, 'test', 'list_item', ['a', 'b'])
        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <list_item>a</list_item>
  <list_item>b</list_item>
</test>
""",
                         doc.toprettyxml(indent="  "))

    def test_add_equal_separated_dict(self):
        doc = self.create_default_doc()

        x.add_equal_separated_dict(doc, 'test', 'dict_item',
                                   {'': 'empty1', None: 'empty2'})
        self.assertEqual("""<?xml version="1.0" ?>
<test/>
""",
                         doc.toprettyxml(indent="  "))

        x.add_equal_separated_dict(doc, 'test', 'dict_item',
                                   {'a': 'b', 'c': 'd'})
        self.assertEqual("""<?xml version="1.0" ?>
<test>
  <dict_item>a=b</dict_item>
  <dict_item>c=d</dict_item>
</test>
""",
                         doc.toprettyxml(indent="  "))

    def create_default_doc(self):
        doc = xml.Document()
        test = doc.createElement('test')
        doc.appendChild(test)
        return doc

    def _get_xml_text(self, strip):
        doc = x.load_xml_document("service/edp/resources/workflow.xml", strip)
        x.add_child(doc, 'action', 'java')
        x.add_text_element_to_tag(doc, 'java', 'sometag', 'somevalue')
        return doc.toprettyxml(indent="  ").split("\n")

    def test_load_xml_document_strip(self):
        # Get the lines from the xml docs
        stripped = set(self._get_xml_text(True))
        unstripped = set(self._get_xml_text(False))

        # Prove they're different
        diff = stripped.symmetric_difference(unstripped)
        self.assertGreater(len(diff), 0)

        # Prove the differences are only blank lines
        non_blank_diffs = [l for l in diff if not l.isspace()]
        self.assertEqual(0, len(non_blank_diffs))
