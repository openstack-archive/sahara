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

import six
import testtools


class MinidomPatchesTest(testtools.TestCase):
    def setUp(self):
        super(MinidomPatchesTest, self).setUp()

    def _generate_n_prettify_xml(self):
        doc = xml.Document()
        pi = doc.createProcessingInstruction('xml-smth',
                                             'type="text/smth" '
                                             'href="test.smth"')
        doc.insertBefore(pi, doc.firstChild)
        configuration = doc.createElement("root")
        doc.appendChild(configuration)
        for idx in six.moves.xrange(0, 5):
            elem = doc.createElement("element")
            configuration.appendChild(elem)
            name = doc.createElement("name")
            elem.appendChild(name)
            name_text = doc.createTextNode("key-%s" % idx)
            name.appendChild(name_text)
            value = doc.createElement("value")
            elem.appendChild(value)
            value_text = doc.createTextNode("value-%s" % idx)
            value.appendChild(value_text)

        return doc.toprettyxml(indent="  ")

    def test_minidom_toprettyxml(self):
        self.assertEqual("""<?xml version="1.0" ?>
<?xml-smth type="text/smth" href="test.smth"?>
<root>
  <element>
    <name>key-0</name>
    <value>value-0</value>
  </element>
  <element>
    <name>key-1</name>
    <value>value-1</value>
  </element>
  <element>
    <name>key-2</name>
    <value>value-2</value>
  </element>
  <element>
    <name>key-3</name>
    <value>value-3</value>
  </element>
  <element>
    <name>key-4</name>
    <value>value-4</value>
  </element>
</root>
""", self._generate_n_prettify_xml())
