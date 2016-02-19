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

import mock
import testtools

from sahara import conductor as cond
from sahara import context
from sahara import exceptions as ex
from sahara.plugins import base as pb
from sahara.plugins.spark import plugin as pl
from sahara.service.edp.spark import engine
from sahara.tests.unit import base
from sahara.utils import edp


conductor = cond.API


class SparkPluginTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(SparkPluginTest, self).setUp()
        self.override_config("plugins", ["spark"])
        pb.setup_plugins()

    def _init_cluster_dict(self, version):
        cluster_dict = {
            'name': 'cluster',
            'plugin_name': 'spark',
            'hadoop_version': version,
            'default_image_id': 'image'}
        return cluster_dict

    def test_plugin09_edp_engine_validation(self):
        cluster_dict = self._init_cluster_dict('0.9.1')

        job = mock.Mock()
        job.type = edp.JOB_TYPE_SPARK

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        edp_engine = plugin.get_edp_engine(cluster, edp.JOB_TYPE_SPARK)
        with testtools.ExpectedException(
                ex.InvalidDataException,
                value_re="Spark 1.3.1 or higher required to run "
                         "Spark jobs\nError ID: .*"):
            edp_engine.validate_job_execution(cluster, job, mock.Mock())

    def test_plugin10_edp_engine(self):
        self._test_engine('1.3.1', edp.JOB_TYPE_SPARK,
                          engine.SparkJobEngine)

    def test_plugin10_shell_engine(self):
        self._test_engine('1.3.1', edp.JOB_TYPE_SHELL,
                          engine.SparkShellJobEngine)

    def test_plugin11_edp_engine(self):
        self._test_engine('1.6.0', edp.JOB_TYPE_SPARK,
                          engine.SparkJobEngine)

    def test_plugin12_shell_engine(self):
        self._test_engine('1.6.0', edp.JOB_TYPE_SHELL,
                          engine.SparkShellJobEngine)

    def _test_engine(self, version, job_type, eng):
        cluster_dict = self._init_cluster_dict(version)

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        self.assertIsInstance(plugin.get_edp_engine(cluster, job_type), eng)

    def test_plugin13_edp_engine(self):
        cluster_dict = {
            'name': 'cluster',
            'plugin_name': 'spark',
            'hadoop_version': '1.3.1',
            'default_image_id': 'image'}

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        self.assertIsInstance(
            plugin.get_edp_engine(cluster, edp.JOB_TYPE_SPARK),
            engine.SparkJobEngine)

    def test_cleanup_configs(self):
        remote = mock.Mock()
        instance = mock.Mock()

        extra_conf = {'job_cleanup': {
            'valid': True,
            'script': 'script_text',
            'cron': 'cron_text'}}
        instance.node_group.node_processes = ["master"]
        instance.node_group.id = id
        cluster_dict = self._init_cluster_dict('1.3.1')

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        plugin._push_cleanup_job(remote, cluster, extra_conf, instance)
        remote.write_file_to.assert_called_with(
            '/etc/hadoop/tmp-cleanup.sh',
            'script_text')
        remote.execute_command.assert_called_with(
            'sudo sh -c \'echo "cron_text" > /etc/cron.d/spark-cleanup\'')

        remote.reset_mock()
        instance.node_group.node_processes = ["worker"]
        plugin._push_cleanup_job(remote, cluster, extra_conf, instance)
        self.assertFalse(remote.called)

        remote.reset_mock()
        instance.node_group.node_processes = ["master"]
        extra_conf['job_cleanup']['valid'] = False
        plugin._push_cleanup_job(remote, cluster, extra_conf, instance)
        remote.execute_command.assert_called_with(
            'sudo rm -f /etc/crond.d/spark-cleanup')


class SparkProviderTest(base.SaharaTestCase):
    def setUp(self):
        super(SparkProviderTest, self).setUp()

    def test_supported_job_types(self):
        provider = pl.SparkProvider()

        res = provider.get_edp_job_types()
        self.assertEqual([edp.JOB_TYPE_SHELL, edp.JOB_TYPE_SPARK],
                         res['1.3.1'])
        self.assertEqual([edp.JOB_TYPE_SHELL, edp.JOB_TYPE_SPARK],
                         res['1.6.0'])

    def test_edp_config_hints(self):
        provider = pl.SparkProvider()

        res = provider.get_edp_config_hints(edp.JOB_TYPE_SHELL, "1.3.1")
        self.assertEqual({'configs': {}, 'args': [], 'params': {}},
                         res['job_config'])

        res = provider.get_edp_config_hints(edp.JOB_TYPE_SHELL, "1.6.0")
        self.assertEqual({'configs': {}, 'args': [], 'params': {}},
                         res['job_config'])

        res = provider.get_edp_config_hints(edp.JOB_TYPE_SPARK, "1.3.1")
        self.assertEqual({'args': [], 'configs': []},
                         res['job_config'])

        res = provider.get_edp_config_hints(edp.JOB_TYPE_SPARK, "1.6.0")
        self.assertEqual({'args': [], 'configs': []},
                         res['job_config'])
