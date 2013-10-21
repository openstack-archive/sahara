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

import savanna.plugins.hdp.services as s
import unittest2


class ServicesTest(unittest2.TestCase):
    #TODO(jspeidel): test remaining service functionality which isn't
    # tested by coarser grained unit tests.

    def test_create_hdfs_service(self):
        service = s.create_service('HDFS')
        self.assertEqual('HDFS', service.name)
        expected_configs = set(['global', 'core-site', 'hdfs-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())

    def test_create_mr_service(self):
        service = s.create_service('MAPREDUCE')
        self.assertEqual('MAPREDUCE', service.name)
        expected_configs = set(['global', 'core-site', 'mapred-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())

    def test_create_hive_service(self):
        service = s.create_service('HIVE')
        self.assertEqual('HIVE', service.name)
        expected_configs = set(['global', 'core-site', 'hive-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_webhcat_service(self):
        service = s.create_service('WEBHCAT')
        self.assertEqual('WEBHCAT', service.name)
        expected_configs = set(['global', 'core-site', 'webhcat-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_zk_service(self):
        service = s.create_service('ZOOKEEPER')
        self.assertEqual('ZOOKEEPER', service.name)
        expected_configs = set(['global', 'core-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_ganglia_service(self):
        service = s.create_service('GANGLIA')
        self.assertEqual('GANGLIA', service.name)
        expected_configs = set(['global', 'core-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertFalse(service.is_mandatory())

    def test_create_ambari_service(self):
        service = s.create_service('AMBARI')
        self.assertEqual('AMBARI', service.name)
        expected_configs = set(['global', 'core-site'])
        self.assertEqual(expected_configs,
                         expected_configs & service.configurations)
        self.assertTrue(service.is_mandatory())
