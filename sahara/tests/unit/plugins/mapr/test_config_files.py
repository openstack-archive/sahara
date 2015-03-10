# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import sahara.plugins.mapr.domain.configuration_file as conf_f
import sahara.tests.unit.base as b


class TestHadoopXML(b.SaharaTestCase):
    def __init__(self, *args, **kwds):
        super(TestHadoopXML, self).__init__(*args, **kwds)
        self.content = '''<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>key1</name>
        <value>value1</value>
    </property>
    <property>
        <name>key2</name>
        <value>value2</value>
    </property>
</configuration>'''

    def test_remote_path(self):
        foo = conf_f.HadoopXML('foo')
        foo.remote_path = '/bar'
        self.assertEqual('/bar/foo', foo.remote_path)

    def test_parse(self):
        foo = conf_f.HadoopXML('foo')
        foo.parse(self.content)
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertDictEqual(expected, foo._config_dict)

    def test_render(self):
        foo = conf_f.HadoopXML('foo')
        expected = {'ke1': 'value1', 'key2': 'value2'}
        foo._config_dict = expected
        actual = foo.render()
        bar = conf_f.HadoopXML('bar')
        bar.parse(actual)
        self.assertDictEqual(expected, bar._config_dict)

    def test_add_property(self):
        foo = conf_f.HadoopXML('foo')
        self.assertDictEqual(foo._config_dict, {})
        foo.add_property('key1', 'value1')
        self.assertDictEqual(foo._config_dict, {'key1': 'value1'})
        foo.add_property('key2', 'value2')
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertDictEqual(expected, foo._config_dict)

    def test_get_config_value(self):
        foo = conf_f.HadoopXML('foo')
        foo._config_dict = {'foo': 'bar'}
        self.assertEqual('bar', foo._get_config_value('foo'))
        self.assertIsNone(foo._get_config_value('bar'))


class TestRawFile(b.SaharaTestCase):
    def __init__(self, *args, **kwds):
        super(TestRawFile, self).__init__(*args, **kwds)
        self.content = 'some meaningful text'

    def test_remote_path(self):
        foo = conf_f.RawFile('foo')
        foo.remote_path = '/bar'
        self.assertEqual('/bar/foo', foo.remote_path)

    def test_parse(self):
        foo = conf_f.RawFile('foo')
        foo.parse(self.content)
        expected = {'content': self.content}
        self.assertDictEqual(expected, foo._config_dict)

    def test_render(self):
        foo = conf_f.RawFile('foo')
        expected = {'content': 'foo bar'}
        foo._config_dict = expected
        actual = foo.render()
        bar = conf_f.RawFile('bar')
        bar.parse(actual)
        self.assertDictEqual(expected, bar._config_dict)


class TestPropertiesFile(b.SaharaTestCase):
    def __init__(self, *args, **kwds):
        super(TestPropertiesFile, self).__init__(*args, **kwds)
        self.content = '''
key1=value1
key2=value2
'''

    def test_remote_path(self):
        foo = conf_f.PropertiesFile('foo')
        foo.remote_path = '/bar'
        self.assertEqual('/bar/foo', foo.remote_path)

    def test_parse(self):
        foo = conf_f.PropertiesFile('foo')
        foo.parse(self.content)
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertDictEqual(expected, foo._config_dict)

    def test_render(self):
        foo = conf_f.PropertiesFile('foo')
        expected = {'ke1': 'value1', 'key2': 'value2'}
        foo._config_dict = expected
        actual = foo.render()
        bar = conf_f.PropertiesFile('bar')
        bar.parse(actual)
        self.assertDictEqual(expected, bar._config_dict)

    def test_add_property(self):
        foo = conf_f.PropertiesFile('foo')
        expected = {}
        self.assertDictEqual(expected, foo._config_dict)

        foo.add_property('key1', 'value1')
        expected = {'key1': 'value1'}
        self.assertDictEqual(expected, foo._config_dict)

        foo.add_property('key2', 'value2')
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertDictEqual(expected, foo._config_dict)

    def test_get_config_value(self):
        foo = conf_f.PropertiesFile('foo')
        foo._config_dict = {'foo': 'bar'}
        self.assertEqual('bar', foo._get_config_value('foo'))
        self.assertIsNone(foo._get_config_value('bar'))


class TestTemplateFile(b.SaharaTestCase):
    def __init__(self, *args, **kwds):
        super(TestTemplateFile, self).__init__(*args, **kwds)
        self.content = '''
key1={{ value1 }}
key2={{ value2 }}'''
        self.rendered = '''
key1=value1
key2=value2'''

    def test_remote_path(self):
        foo = conf_f.TemplateFile('foo')
        foo.remote_path = '/bar'
        self.assertEqual('/bar/foo', foo.remote_path)

    def test_parse(self):
        foo = conf_f.TemplateFile('foo')
        foo.parse(self.content)
        self.assertIsNotNone(foo._template)

    def test_render(self):
        foo = conf_f.TemplateFile('foo')
        expected = {'value1': 'value1', 'value2': 'value2'}
        foo.parse(self.content)
        foo._config_dict = expected
        actual = foo.render()
        self.assertEqual(self.rendered, actual)

    def test_add_property(self):
        foo = conf_f.TemplateFile('foo')
        expected = {}
        self.assertDictEqual(expected, foo._config_dict)

        foo.add_property('key1', 'value1')
        expected = {'key1': 'value1'}
        self.assertDictEqual(expected, foo._config_dict)

        foo.add_property('key2', 'value2')
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertDictEqual(expected, foo._config_dict)


class TestEnvironmentConfig(b.SaharaTestCase):
    def __init__(self, *args, **kwds):
        super(TestEnvironmentConfig, self).__init__(*args, **kwds)
        self.content = '''
non export line
export key1=value1
export key2=value2
export key
'''

    def test_remote_path(self):
        foo = conf_f.EnvironmentConfig('foo')
        foo.remote_path = '/bar'
        self.assertEqual('/bar/foo', foo.remote_path)

    def test_parse(self):
        foo = conf_f.EnvironmentConfig('foo')
        foo.parse(self.content)
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertDictEqual(expected, foo._config_dict)

    def test_render(self):
        foo = conf_f.EnvironmentConfig('foo')
        expected = {'ke1': 'value1', 'key2': 'value2'}
        foo._config_dict = expected
        actual = foo.render()
        bar = conf_f.EnvironmentConfig('bar')
        bar.parse(actual)
        self.assertDictEqual(expected, bar._config_dict)

    def test_render_extra_properties(self):
        foo = conf_f.EnvironmentConfig('foo')
        foo.parse(self.content)
        foo.add_property('key3', 'value3')
        foo_content = foo.render()
        bar = conf_f.EnvironmentConfig('bar')
        bar.parse(foo_content)
        expected = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        self.assertDictEqual(expected, bar._config_dict)

    def test_add_property(self):
        foo = conf_f.EnvironmentConfig('foo')
        self.assertDictEqual({}, foo._config_dict)
        foo.add_property('key1', 'value1')
        self.assertDictEqual({'key1': 'value1'}, foo._config_dict)
        foo.add_property('key2', 'value2')
        expected = {'key1': 'value1', 'key2': 'value2'}
        self.assertDictEqual(expected, foo._config_dict)

    def test_get_config_value(self):
        foo = conf_f.EnvironmentConfig('foo')
        foo._config_dict = {'foo': 'bar'}
        self.assertEqual('bar', foo._get_config_value('foo'))
        self.assertIsNone(foo._get_config_value('bar'))
