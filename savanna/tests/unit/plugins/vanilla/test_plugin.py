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

from savanna.plugins.general import exceptions as ex
from savanna.plugins.vanilla import config_helper as c_h
from savanna.plugins.vanilla import mysql_helper as m_h
from savanna.plugins.vanilla import plugin as p
from savanna.tests.unit.plugins.vanilla import test_utils as tu


class VanillaPluginTest(unittest2.TestCase):
    def setUp(self):
        self.pl = p.VanillaProvider()

    def test_validate(self):
        self.ng = []
        self.ng.append(tu._make_ng_dict("nn", "f1", ["namenode"], 0))
        self.ng.append(tu._make_ng_dict("jt", "f1", ["jobtracker"], 0))
        self.ng.append(tu._make_ng_dict("tt", "f1", ["tasktracker"], 0))
        self.ng.append(tu._make_ng_dict("oozie", "f1", ["oozie"], 0))

        self._validate_case(1, 1, 10, 1)

        with self.assertRaises(ex.NotSingleNameNodeException):
            self._validate_case(0, 1, 10, 1)
        with self.assertRaises(ex.NotSingleNameNodeException):
            self._validate_case(2, 1, 10, 1)

        with self.assertRaises(ex.TaskTrackersWithoutJobTracker):
            self._validate_case(1, 0, 10, 1)
        with self.assertRaises(ex.NotSingleJobTrackerException):
            self._validate_case(1, 2, 10, 1)

        with self.assertRaises(ex.NotSingleOozieException):
            self._validate_case(1, 1, 0, 2)
        with self.assertRaises(ex.OozieWithoutJobTracker):
            self._validate_case(1, 0, 0, 1)

    def _validate_case(self, *args):
        lst = []
        for i in range(0, len(args)):
            self.ng[i]['count'] = args[i]
            lst.append(self.ng[i])

        cl = tu._create_cluster("cluster1", "tenant1", "vanilla", "1.2.1", lst)

        self.pl.validate(cl)

    def test_get_configs(self):
        cl_configs = self.pl.get_configs("1.2.1")
        for cfg in cl_configs:
            if cfg.config_type is "bool":
                self.assertIsInstance(cfg.default_value, bool)
            elif cfg.config_type is "int":
                self.assertIsInstance(cfg.default_value, int)
            else:
                self.assertIsInstance(cfg.default_value, str)
            self.assertNotIn(cfg.name, c_h.HIDDEN_CONFS)

    def test_extract_environment_configs(self):
        env_configs = {
            "JobFlow": {
                'Oozie Heap Size': 4000
            },
            "MapReduce": {
                'Job Tracker Heap Size': 1000,
                'Task Tracker Heap Size': "2000"
            },
            "HDFS": {
                'Name Node Heap Size': 3000,
                'Data Node Heap Size': "4000"
            },
            "Wrong-applicable-target": {
                't1': 4
            }}
        self.assertListEqual(c_h.extract_environment_confs(env_configs),
                             ['HADOOP_NAMENODE_OPTS=\\"-Xmx3000m\\"',
                              'HADOOP_DATANODE_OPTS=\\"-Xmx4000m\\"',
                              'CATALINA_OPTS=\\"-Xmx4000m\\"',
                              'HADOOP_JOBTRACKER_OPTS=\\"-Xmx1000m\\"',
                              'HADOOP_TASKTRACKER_OPTS=\\"-Xmx2000m\\"'])

    def test_extract_xml_configs(self):
        xml_configs = {
            "HDFS": {
                'dfs.replication': 3,
                'fs.default.name': 'hdfs://',
                'key': 'value'
            },
            "MapReduce": {
                'io.sort.factor': 10,
                'mapred.reduce.tasks': 2
            },
            "Wrong-applicable-target": {
                'key': 'value'
            }
        }

        self.assertListEqual(c_h.extract_xml_confs(xml_configs),
                             [('fs.default.name', 'hdfs://'),
                              ('dfs.replication', 3),
                              ('mapred.reduce.tasks', 2),
                              ('io.sort.factor', 10)])

    def test_general_configs(self):
        gen_config = {
            c_h.ENABLE_SWIFT.name: {
                'default_value': c_h.ENABLE_SWIFT.default_value,
                'conf': {
                    'fs.swift.enabled': True
                }
            },
            c_h.ENABLE_MYSQL.name: {
                'default_value': c_h.ENABLE_MYSQL.default_value,
                'conf': {
                    'oozie.service.JPAService.jdbc.username': 'oozie'
                }
            }
        }
        all_configured = {
            'fs.swift.enabled': True,
            'oozie.service.JPAService.jdbc.username': 'oozie'
        }
        configs = {
            'general': {
                'Enable Swift': True
            }
        }
        cfg = c_h.generate_cfg_from_general({}, configs, gen_config)
        self.assertDictEqual(cfg, all_configured)
        configs['general'].update({'Enable MySQL': False})
        cfg = c_h.generate_cfg_from_general({}, configs, gen_config)
        self.assertDictEqual(cfg, {'fs.swift.enabled': True})
        configs['general'].update({
            'Enable Swift': False,
            'Enable MySQL': False
        })
        cfg = c_h.generate_cfg_from_general({}, configs, gen_config)
        self.assertDictEqual(cfg, {})
        configs = {}
        cfg = c_h.generate_cfg_from_general({}, configs, gen_config)
        self.assertDictEqual(cfg, all_configured)

    def test_get_mysql_configs(self):
        cfg = m_h.get_required_mysql_configs(None, None)
        self.assertDictEqual(cfg, m_h.get_oozie_mysql_configs())
        cfg = m_h.get_required_mysql_configs("metastore_host", "passwd")
        cfg_to_compare = m_h.get_oozie_mysql_configs()
        cfg_to_compare.update(m_h.get_hive_mysql_configs(
            "metastore_host", "passwd"))
        self.assertDictEqual(cfg, cfg_to_compare)
