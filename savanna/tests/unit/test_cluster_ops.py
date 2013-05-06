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

from savanna.service.cluster_ops import _create_xml
import unittest


class ConfigGeneratorTest(unittest.TestCase):
    def test_xml_generator(self):
        config = {
            'key-1': 'value-1',
            'key-2': 'value-2',
            'key-3': 'value-3',
            'key-4': 'value-4',
            'key-5': 'value-5',
        }
        xml = _create_xml(config, config.keys())
        self.assertEqual(xml, """<?xml version="1.0" ?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
  <property>
    <name>key-3</name>
    <value>value-3</value>
  </property>
  <property>
    <name>key-2</name>
    <value>value-2</value>
  </property>
  <property>
    <name>key-1</name>
    <value>value-1</value>
  </property>
  <property>
    <name>key-5</name>
    <value>value-5</value>
  </property>
  <property>
    <name>key-4</name>
    <value>value-4</value>
  </property>
</configuration>
""")
