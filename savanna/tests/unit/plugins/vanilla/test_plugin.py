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

from savanna.db import models as m
from savanna.plugins.vanilla import config_helper as c_h
from savanna.plugins.vanilla import exceptions as ex
from savanna.plugins.vanilla import plugin as p


class VanillaPluginTest(unittest2.TestCase):
    def setUp(self):
        self.pl = p.VanillaProvider()
        self.cl = m.Cluster("cluster1", "tenant1", "vanilla", "1.1.2")
        self.ng1 = m.NodeGroup("nn", "f1", ["namenode"], 1)
        self.ng2 = m.NodeGroup("jt", "f1", ["jobtracker"], 1)
        self.ng3 = m.NodeGroup("tt", "f1", ["tasktracker"], 10)
        self.cl_configs = self.pl.get_configs("1.1.2")

    def test_validate(self):
        self.cl.node_groups = [self.ng1]
        self.pl.validate(self.cl)
        with self.assertRaises(ex.NotSingleNameNodeException):
            self.ng1.count = 0
            self.pl.validate(self.cl)
        with self.assertRaises(ex.NotSingleNameNodeException):
            self.ng1.count = 2
            self.pl.validate(self.cl)
        self.ng1.count = 1

        self.cl.node_groups.append(self.ng2)
        self.pl.validate(self.cl)
        with self.assertRaises(ex.NotSingleJobTrackerException):
            self.ng2.count = 2
            self.pl.validate(self.cl)

        self.cl.node_groups.append(self.ng3)
        self.ng2.count = 1
        self.pl.validate(self.cl)
        with self.assertRaises(ex.TaskTrackersWithoutJobTracker):
            self.ng2.count = 0
            self.pl.validate(self.cl)

    def test_get_configs(self):
        for cfg in self.cl_configs:
            if cfg.config_type is "bool":
                self.assertIsInstance(cfg.default_value, bool)
            elif cfg.config_type is "int":
                self.assertIsInstance(cfg.default_value, int)
            else:
                self.assertIsInstance(cfg.default_value, str)
            self.assertNotIn(cfg.name, c_h.HIDDEN_CONFS)

    def test_extract_environment_configs(self):
        env_configs = {
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
