# Copyright (c) 2015 ISPRAS
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
import testtools

from sahara import conductor as cond
from sahara import context
from sahara.plugins import base as pb
from sahara.plugins import exceptions as ex
from sahara.service.edp.spark import engine
from sahara.tests.unit import base
from sahara.utils import edp


conductor = cond.API


class SparkPluginTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(SparkPluginTest, self).setUp()
        self.override_config("plugins", ["cdh"])
        pb.setup_plugins()

    def test_plugin_edp_engine_no_spark(self):
        cluster_dict = {
            'name': 'cluster',
            'plugin_name': 'cdh',
            'hadoop_version': '5.7.0',
            'default_image_id': 'image'}

        job = mock.Mock()
        job.type = edp.JOB_TYPE_SPARK

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        edp_engine = plugin.get_edp_engine(cluster, edp.JOB_TYPE_SPARK)
        with testtools.ExpectedException(
                ex.InvalidComponentCountException,
                value_re="Hadoop cluster should contain 1 "
                         "SPARK_YARN_HISTORY_SERVER component\(s\). Actual "
                         "SPARK_YARN_HISTORY_SERVER count is 0\nError ID: .*"):

            edp_engine.validate_job_execution(cluster, job, mock.Mock())

    def test_plugin_edp_engine(self):
        cluster_dict = {
            'name': 'cluster',
            'plugin_name': 'cdh',
            'hadoop_version': '5.7.0',
            'default_image_id': 'image'}

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        self.assertIsInstance(
            plugin.get_edp_engine(cluster, edp.JOB_TYPE_SPARK),
            engine.SparkJobEngine)
