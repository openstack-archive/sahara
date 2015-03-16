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


from testtools import testcase

from sahara.tests.integration.configs import config as cfg
import sahara.tests.integration.tests.gating.test_mapr_gating as mapr_test


class MapR402MRv2GatingTest(mapr_test.MapRGatingTest):
    mapr_config = cfg.ITConfig().mapr_402mrv2_config
    SKIP_MAP_REDUCE_TEST = mapr_config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = mapr_config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = mapr_config.SKIP_SCALING_TEST
    SKIP_CINDER_TEST = mapr_config.SKIP_CINDER_TEST
    SKIP_EDP_TEST = mapr_config.SKIP_EDP_TEST

    def get_plugin_config(self):
        return MapR402MRv2GatingTest.mapr_config

    def setUp(self):
        super(MapR402MRv2GatingTest, self).setUp()
        self._tt_name = 'nodemanager'
        self._mr_version = 2
        self._node_processes = [
            'NodeManager',
            'ResourceManager',
            'HistoryServer',
            'FileServer',
            'CLDB',
            'ZooKeeper',
            'Oozie',
            'Webserver',
            'Metrics',

            'Sqoop2-Server',
            'Sqoop2-Client',
            'Pig',
            'Mahout',
            'Hue',
            'HTTPFS',
            'HiveMetastore',
            'HiveServer2',
            'Flume',
            'Drill'
        ]
        self._master_node_processes = [
            'Flume',
            'Hue',
            'Metrics',
            'Webserver',
            'ZooKeeper',
            'HTTPFS',
            'NodeManager',
            'HistoryServer',
            'ResourceManager',
            'Oozie',
            'FileServer',
            'CLDB',
        ]
        self._worker_node_processes = [
            'NodeManager',
            'HiveServer2',
            'HiveMetastore',
            'FileServer',
            'Sqoop2-Client',
            'Sqoop2-Server',
        ]

    @testcase.skipIf(
        cfg.ITConfig().mapr_402mrv2_config.SKIP_ALL_TESTS_FOR_PLUGIN,
        "All tests for MapR plugin were skipped")
    @testcase.attr('mapr402mrv2')
    def test_mapr_plugin_gating(self):
        super(MapR402MRv2GatingTest, self).test_mapr_plugin_gating()
