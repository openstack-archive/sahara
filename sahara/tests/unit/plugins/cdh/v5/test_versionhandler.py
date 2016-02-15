# Copyright (c) 2015 Intel Corporation.
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
import six

from sahara.plugins.cdh.v5.edp_engine import EdpOozieEngine
from sahara.plugins.cdh.v5 import versionhandler
from sahara.tests.unit import base


class VersionHandlerTestCase(base.SaharaTestCase):

    plugin_path = "sahara.plugins.cdh.v5."
    cloudera_utils_path = plugin_path + "cloudera_utils.ClouderaUtilsV5."
    plugin_utils_path = plugin_path + "plugin_utils.PluginUtilsV5."

    def setUp(self):
        super(VersionHandlerTestCase, self).setUp()
        self.vh = versionhandler.VersionHandler()

    def test_get_node_processes(self):
        processes = self.vh.get_node_processes()
        for k, v in six.iteritems(processes):
            for p in v:
                self.assertIsInstance(p, str)

    @mock.patch("sahara.conductor.API.cluster_update")
    @mock.patch("sahara.context.ctx")
    @mock.patch(plugin_path + "deploy.configure_cluster")
    @mock.patch(cloudera_utils_path + "get_cloudera_manager_info",
                return_value={"fake_cm_info": "fake"})
    def test_config_cluster(self, get_cm_info, configure_cluster,
                            ctx, cluster_update):
        cluster = mock.Mock()
        self.vh.configure_cluster(cluster)
        configure_cluster.assert_called_once_with(cluster)
        cluster_update.assert_called_once_with(
            ctx(), cluster,
            {'info': {"fake_cm_info": "fake"}})

    @mock.patch(plugin_path + "deploy.start_cluster")
    def test_start_cluster(self, start_cluster):
        cluster = mock.Mock()
        self.vh._set_cluster_info = mock.Mock()
        self.vh.start_cluster(cluster)
        start_cluster.assert_called_once_with(cluster)
        self.vh._set_cluster_info.assert_called_once_with(cluster)

    @mock.patch(plugin_path + "deploy.decommission_cluster")
    def test_decommmission_nodes(self, decommission_cluster):
        cluster = mock.Mock()
        instances = mock.Mock()
        self.vh.decommission_nodes(cluster, instances)
        decommission_cluster.assert_called_once_with(cluster,
                                                     instances)

    @mock.patch(plugin_path + "deploy.scale_cluster")
    def test_scale_cluster(self, scale_cluster):
        cluster = mock.Mock()
        instances = mock.Mock()
        self.vh.scale_cluster(cluster, instances)
        scale_cluster.assert_called_once_with(cluster, instances)

    @mock.patch("sahara.conductor.API.cluster_update")
    @mock.patch("sahara.context.ctx")
    @mock.patch(cloudera_utils_path + "get_cloudera_manager_info",
                return_value={})
    @mock.patch(plugin_utils_path + "get_hue")
    def test_set_cluster_info(self, get_hue, get_cloudera_manager_info,
                              ctx, cluster_update):
        get_hue.return_value.management_ip = "1.2.3.4"
        cluster = mock.Mock()
        self.vh._set_cluster_info(cluster)
        info = {'info': {'Hue Dashboard': {'Web UI': 'http://1.2.3.4:8888'}}}
        cluster_update.assert_called_once_with(ctx(), cluster, info)

    @mock.patch("sahara.service.edp.job_utils.get_plugin")
    def test_get_edp_engine(self, get_plugin):
        cluster = mock.Mock()
        job_type = 'Java'
        ret = self.vh.get_edp_engine(cluster, job_type)
        self.assertIsInstance(ret, EdpOozieEngine)

        job_type = 'unsupported'
        ret = self.vh.get_edp_engine(cluster, job_type)
        self.assertIsNone(ret)

    def test_get_edp_job_types(self):
        ret = self.vh.get_edp_job_types()
        self.assertEqual(EdpOozieEngine.get_supported_job_types(), ret)

    @mock.patch(plugin_path +
                "edp_engine.EdpOozieEngine.get_possible_job_config",
                return_value={'job_config': {}})
    def test_edp_config_hints(self, get_possible_job_config):
        job_type = mock.Mock()
        ret = self.vh.get_edp_config_hints(job_type)
        get_possible_job_config.assert_called_once_with(job_type)
        self.assertEqual(ret, {'job_config': {}})

    @mock.patch(plugin_path + "deploy.get_open_ports", return_value=[1234])
    def test_get_open_ports(self, get_open_ports):
        node_group = mock.Mock()
        ret = self.vh.get_open_ports(node_group)
        get_open_ports.assert_called_once_with(node_group)
        self.assertEqual(ret, [1234])

    @mock.patch(plugin_utils_path + "recommend_configs")
    def test_recommend_configs(self, recommend_configs):
        cluster = mock.Mock()
        scaling = mock.Mock()
        self.vh.get_plugin_configs = mock.Mock()
        self.vh.recommend_configs(cluster, scaling)
        recommend_configs.assert_called_once_with(cluster,
                                                  self.vh.get_plugin_configs(),
                                                  scaling)
