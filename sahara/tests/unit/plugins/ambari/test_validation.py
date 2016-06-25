# Copyright (c) 2015 Mirantis Inc.
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


import mock

from sahara.plugins.ambari import common as p_common
from sahara.plugins.ambari import plugin
from sahara.plugins import exceptions
from sahara.tests.unit import base


def make_cluster(processes_map):
    m = mock.Mock()
    ngs = []
    for count, processes in processes_map.items():
        ng = mock.Mock()
        ng.count = count
        ng.node_processes = processes
        ngs.append(ng)
    m.node_groups = ngs
    return m


class AmbariValidationTestCase(base.SaharaTestCase):
    def setUp(self):
        super(AmbariValidationTestCase, self).setUp()
        self.plugin = plugin.AmbariPluginProvider()

    def test_cluster_with_ambari(self):
        cluster = make_cluster({1: [p_common.AMBARI_SERVER,
                                    p_common.ZOOKEEPER_SERVER,
                                    p_common.NAMENODE,
                                    p_common.DATANODE,
                                    p_common.RESOURCEMANAGER,
                                    p_common.NODEMANAGER,
                                    p_common.HISTORYSERVER,
                                    p_common.APP_TIMELINE_SERVER,
                                    p_common.SECONDARY_NAMENODE]})
        cluster.cluster_configs = {"general": {}}
        with mock.patch("sahara.plugins.ambari.validation.conductor") as p:
            p.cluster_get = mock.Mock()
            p.cluster_get.return_value = cluster
            self.assertIsNone(self.plugin.validate(cluster))

    def test_cluster_without_ambari(self):
        cluster = make_cluster({1: ["spam"]})
        with mock.patch("sahara.plugins.ambari.validation.conductor") as p:
            p.cluster_get = mock.Mock()
            p.cluster_get.return_value = cluster
            self.assertRaises(exceptions.InvalidComponentCountException,
                              self.plugin.validate, cluster)
