# Copyright (c) 2013 Hortonworks, Inc.
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

import collections as c
import json
import os
from savanna.db import models as m
from savanna.plugins.hdp import blueprintprocessor as bp
import unittest2


class BlueprintProcessorTest(unittest2.TestCase):
    def setUp(self):
        pass

    def _xpath_get(self, mydict, path):
        elem = mydict
        try:
            for x in path.strip("/").split("/"):
                try:
                    x = int(x)
                    elem = elem[x]
                except ValueError:
                    elem = elem.get(x)
        except Exception:
            pass

        return elem

    def test_existing_config_item_in_top_level_within_blueprint(self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        config_items = [
            {"value": "/some/new/path",
             "config": {
                 "name": "dfs_name_dir",
                 "description": "blah blah",
                 "config_type": "string",
                 "is_optional": "true",
                 "default_value": "/hadoop/hdfs/namenode",
                 "applicable_target": "general",
                 "file": "global",
                 "scope": "cluster"}
             }
        ]
        # verify this config item already exists in the blueprint
        prop_name = self._xpath_get(processor.blueprint,
                                    '/configurations/0/properties/0/name')
        self.assertEqual('dfs_name_dir', prop_name,
                         'dfs_name_dir not found in bluerpint')

        # convert the json structure into a proper object
        configs_list = self.json2obj(json.dumps(config_items))

        # process the input configuration
        processor.process_user_inputs(configs_list)
        prop_name = self._xpath_get(processor.blueprint,
                                    '/configurations/0/properties/0/name')
        self.assertEqual('dfs_name_dir', prop_name,
                         'dfs_name_dir not found in bluerpint post config '
                         'processing')
        prop_value = self._xpath_get(processor.blueprint,
                                     '/configurations/0/properties/0/value')
        self.assertEqual('/some/new/path', prop_value,
                         'prop value is wrong post config processing')

    def test_insert_new_config_item_into_existing_top_level_configuration(
            self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        config_items = [
            {"value": "512m",
             "config": {
                 "name": "namenode_heapsize",
                 "description": "heap size",
                 "default_value": "256m",
                 "config_type": "string",
                 "is_optional": "true",
                 "applicable_target": "general",
                 "file": "global",
                 "scope": "cluster"}
             }
        ]
        # verify this config section already exists in the blueprint,
        # but doesn't have the given property
        props_for_global = self._xpath_get(processor.blueprint,
                                           '/configurations/0/properties')
        prop_dict = processor._find_blueprint_section(props_for_global, 'name',
                                                      'namenode_heapsize')
        self.assertIsNone(prop_dict, 'no matching property should be found')

        configs_list = self.json2obj(json.dumps(config_items))

        # process the input configuration
        processor.process_user_inputs(configs_list)
        prop_dict = processor._find_blueprint_section(props_for_global, 'name',
                                                      'namenode_heapsize')
        self.assertIsNotNone(prop_dict, 'no matching property should be found')

    def test_insert_new_config_item_into_newly_created_top_level_configuration(
            self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        config_items = [
            {"value": "50",
             "config": {
                 "name": "mapred.job.tracker.handler.count",
                 "description": "job tracker handler count",
                 "config_type": "integer",
                 "applicable_target": "general",
                 "is_optional": "true",
                 "file": "mapred-site",
                 "scope": "node"}
             }
        ]
        # verify the config with this tag does not exist
        configs = self._xpath_get(processor.blueprint, '/configurations')
        self.assertNotEqual('mapred-site', configs[0]['name'],
                            'section should not exist')

        configs_list = self.json2obj(json.dumps(config_items))

        # process the input configuration
        processor.process_user_inputs(configs_list)
        configs = self._xpath_get(processor.blueprint, '/configurations')
        self.assertEqual(2, len(configs), 'no config section added')
        self.assertEqual('mapred-site', configs[1]['name'],
                         'section should exist')
        self.assertEqual('mapred.job.tracker.handler.count',
                         configs[1]['properties'][0]['name'],
                         'property not added')

    def test_insert_host_mappings(self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        node_groups = []
        node_groups.append(m.NodeGroup('MASTER', 'master-flavor',
                                       ["namenode", "jobtracker",
                                       "secondary_namenode", "ganglia_server",
                                       "ganglia_monitor", "nagios_server",
                                       "ambari_server", "ambari_agent"], 1,
                                       image_id='master-img'))
        node_groups.append(m.NodeGroup('SLAVE', 'slave-flavor',
                                       ["datanode", "tasktracker",
                                       "ganglia_monitor", "hdfs_client",
                                       "mapreduce_client", "ambari_agent"], 2,
                                       image_id='slave-img'))

        processor.process_node_groups(node_groups)
        host_mappings = processor.blueprint['host_role_mappings']
        self.assertEqual(2, len(host_mappings),
                         'wrong number of host role mappings')
        expected_master_dict = {
            "name": "MASTER",
            "components": [
                {"name": "NAMENODE"},
                {"name": "JOBTRACKER"},
                {"name": "SECONDARY_NAMENODE"},
                {"name": "GANGLIA_SERVER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "NAGIOS_SERVER"},
                {"name": "AMBARI_SERVER"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1"
                }
            ]
        }
        self.assertDictEqual(expected_master_dict, host_mappings[0],
                             'first mapping does not match')
        expected_slave_dict = {
            "name": "SLAVE",
            "components": [
                {"name": "DATANODE"},
                {"name": "TASKTRACKER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "HDFS_CLIENT"},
                {"name": "MAPREDUCE_CLIENT"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1+"
                }
            ]
        }
        self.assertDictEqual(expected_slave_dict, host_mappings[1],
                             'second mapping does not match')

    def test_leave_existing_host_mapping_alone(self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        node_groups = []
        node_groups.append(m.NodeGroup('OTHER_MASTER_GROUP', 'master-flavor',
                                       ["namenode", "jobtracker",
                                       "secondary_namenode", "ganglia_server",
                                       "ganglia_monitor", "nagios_server",
                                       "ambari_server", "ambari_agent"], 1,
                                       image_id='master-img'))
        processor.process_node_groups(node_groups)
        host_mappings = processor.blueprint['host_role_mappings']
        self.assertEqual(3, len(host_mappings),
                         'wrong number of host role mappings')
        expected_master_dict = {
            "name": "MASTER",
            "components": [
                {"name": "NAMENODE"},
                {"name": "JOBTRACKER"},
                {"name": "SECONDARY_NAMENODE"},
                {"name": "GANGLIA_SERVER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "NAGIOS_SERVER"},
                {"name": "AMBARI_SERVER"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1"
                }
            ]
        }
        self.assertDictEqual(expected_master_dict, host_mappings[0],
                             'first mapping does not match')
        expected_other_master_dict = {
            "name": "OTHER_MASTER_GROUP",
            "components": [
                {"name": "NAMENODE"},
                {"name": "JOBTRACKER"},
                {"name": "SECONDARY_NAMENODE"},
                {"name": "GANGLIA_SERVER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "NAGIOS_SERVER"},
                {"name": "AMBARI_SERVER"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1"
                }
            ]
        }
        self.assertDictEqual(expected_other_master_dict, host_mappings[2],
                             'first mapping does not match')

    def test_overwrite_existing_host_role_mapping(self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        node_groups = []
        node_groups.append(m.NodeGroup('MASTER', 'master-flavor',
                                       ["namenode", "jobtracker",
                                       "secondary_namenode", "ganglia_server",
                                       "ganglia_monitor", "ambari_server",
                                       "ambari_agent"], 1,
                                       image_id='master-img'))
        processor.process_node_groups(node_groups)
        host_mappings = processor.blueprint['host_role_mappings']
        self.assertEqual(2, len(host_mappings),
                         'wrong number of host role mappings')
        expected_master_dict = {
            "name": "MASTER",
            "components": [
                {"name": "NAMENODE"},
                {"name": "JOBTRACKER"},
                {"name": "SECONDARY_NAMENODE"},
                {"name": "GANGLIA_SERVER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "AMBARI_SERVER"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1"
                }
            ]
        }
        self.assertDictEqual(expected_master_dict, host_mappings[0],
                             'first mapping does not match')
        expected_slave_dict = {
            "name": "SLAVE",
            "components": [
                {"name": "DATANODE"},
                {"name": "TASKTRACKER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "HDFS_CLIENT"},
                {"name": "MAPREDUCE_CLIENT"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1+"
                }
            ]
        }
        self.assertDictEqual(expected_slave_dict, host_mappings[1],
                             'second mapping does not match')

    def test_null_node_processes_specified(self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        node_groups = []
        node_groups.append(
            m.NodeGroup('MASTER', 'master-flavor', [], 1,
                        image_id='master-img'))
        node_groups.append(
            m.NodeGroup('SLAVE', 'slave-flavor', [], 2, image_id='slave-img'))

        processor.process_node_groups(node_groups)
        host_mappings = processor.blueprint['host_role_mappings']
        self.assertEqual(2, len(host_mappings),
                         'wrong number of host role mappings')
        expected_master_dict = {
            "name": "MASTER",
            "components": [
                {"name": "NAMENODE"},
                {"name": "JOBTRACKER"},
                {"name": "SECONDARY_NAMENODE"},
                {"name": "GANGLIA_SERVER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "NAGIOS_SERVER"},
                {"name": "AMBARI_SERVER"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1"
                }
            ]
        }
        self.assertDictEqual(expected_master_dict, host_mappings[0],
                             'first mapping does not match')
        expected_slave_dict = {
            "name": "SLAVE",
            "components": [
                {"name": "DATANODE"},
                {"name": "TASKTRACKER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "HDFS_CLIENT"},
                {"name": "MAPREDUCE_CLIENT"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1+"
                }
            ]
        }
        self.assertDictEqual(expected_slave_dict, host_mappings[1],
                             'second mapping does not match')

    def test_empty_node_processes_specified(self):
        processor = bp.BlueprintProcessor(
            json.load(open(
                os.path.join(os.path.realpath('./unit/plugins'), 'hdp',
                             'resources',
                             'sample-ambari-blueprint.json'), 'r')))
        node_groups = []
        node_groups.append(
            m.NodeGroup('MASTER', 'master-flavor', [], 1,
                        image_id='master-img'))
        node_groups.append(
            m.NodeGroup('SLAVE', 'slave-flavor', [], 2, image_id='slave-img'))

        processor.process_node_groups(node_groups)
        host_mappings = processor.blueprint['host_role_mappings']
        self.assertEqual(2, len(host_mappings),
                         'wrong number of host role mappings')
        expected_master_dict = {
            "name": "MASTER",
            "components": [
                {"name": "NAMENODE"},
                {"name": "JOBTRACKER"},
                {"name": "SECONDARY_NAMENODE"},
                {"name": "GANGLIA_SERVER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "NAGIOS_SERVER"},
                {"name": "AMBARI_SERVER"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1"
                }
            ]
        }
        self.assertDictEqual(expected_master_dict, host_mappings[0],
                             'first mapping does not match')
        expected_slave_dict = {
            "name": "SLAVE",
            "components": [
                {"name": "DATANODE"},
                {"name": "TASKTRACKER"},
                {"name": "GANGLIA_MONITOR"},
                {"name": "HDFS_CLIENT"},
                {"name": "MAPREDUCE_CLIENT"},
                {"name": "AMBARI_AGENT"}
            ],
            "hosts": [
                {
                    "cardinality": "1+"
                }
            ]
        }
        self.assertDictEqual(expected_slave_dict, host_mappings[1],
                             'second mapping does not match')

    def _json_object_hook(self, d):
        return c.namedtuple('X', d.keys())(*d.values())

    def json2obj(self, data):
        return json.loads(data, object_hook=self._json_object_hook)
