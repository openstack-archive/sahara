# Copyright (c) 2015 Intel Corporation
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

from sahara import exceptions as ex
from sahara.plugins import base as pb
from sahara.plugins.cdh.v5_4_0 import edp_engine
from sahara.plugins import exceptions as pl_ex
from sahara.tests.unit import base as sahara_base
from sahara.tests.unit.plugins.cdh import utils as c_u
from sahara.utils import edp


def get_cluster(version='5.4.0'):
    cluster = c_u.get_fake_cluster(plugin_name='CDH', hadoop_version=version)
    return cluster


class EdpEngineTestV540(sahara_base.SaharaTestCase):

    def setUp(self):
        super(EdpEngineTestV540, self).setUp()
        pb.setup_plugins()

    def test_get_hdfs_user(self):
        eng = edp_engine.EdpOozieEngine(get_cluster())
        self.assertEqual('hdfs', eng.get_hdfs_user())

    @mock.patch('sahara.service.edp.hdfs_helper.create_dir_hadoop2')
    def test_create_hdfs_dir(self, create_dir_hadoop2):
        eng = edp_engine.EdpOozieEngine(get_cluster())
        remote = mock.Mock()
        dir_name = mock.Mock()
        eng.create_hdfs_dir(remote, dir_name)
        create_dir_hadoop2.assert_called_once_with(remote,
                                                   dir_name,
                                                   eng.get_hdfs_user())

    def test_get_oozie_server_uri(self):
        cluster = get_cluster()
        eng = edp_engine.EdpOozieEngine(cluster)
        uri = eng.get_oozie_server_uri(cluster)
        self.assertEqual("http://1.2.3.5:11000/oozie", uri)

    def test_get_name_node_uri(self):
        cluster = get_cluster()
        eng = edp_engine.EdpOozieEngine(cluster)
        uri = eng.get_name_node_uri(cluster)
        self.assertEqual("hdfs://master_inst.novalocal:8020", uri)

        # has HDFS_JOURNALNODE
        cluster = get_cluster()
        jns_node_group = mock.MagicMock()
        jns_node_group.node_processes = ['HDFS_JOURNALNODE']
        jns_node_group.instances = [mock.Mock()]
        list.append(cluster.node_groups, jns_node_group)
        uri = eng.get_name_node_uri(cluster)
        self.assertEqual("hdfs://nameservice01", uri)

    def test_get_resource_manager_uri(self):
        cluster = get_cluster()
        eng = edp_engine.EdpOozieEngine(cluster)
        uri = eng.get_resource_manager_uri(cluster)
        self.assertEqual("master_inst.novalocal:8032", uri)

    def test_get_oozie_server(self):
        cluster = get_cluster()
        eng = edp_engine.EdpOozieEngine(cluster)
        actual = eng.get_oozie_server(cluster)
        expect = cluster.node_groups[1].instances[0]
        self.assertEqual(expect, actual)

    @mock.patch('sahara.service.edp.oozie.engine.'
                'OozieJobEngine.validate_job_execution')
    def test_validate_job_execution(self, c):
        cluster = get_cluster()
        eng = edp_engine.EdpOozieEngine(cluster)
        eng.validate_job_execution(cluster, mock.Mock(), mock.Mock())

        # more than one oozie server
        dict.__setitem__(cluster.node_groups[1], 'count', 2)
        self.assertRaises(pl_ex.InvalidComponentCountException,
                          eng.validate_job_execution, cluster,
                          mock.Mock(), mock.Mock())

    @mock.patch(
        'sahara.plugins.cdh.confighints_helper.get_possible_hive_config_from',
        return_value={})
    def test_get_possible_job_config_hive(self,
                                          get_possible_hive_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_HIVE)
        get_possible_hive_config_from.assert_called_once_with(
            'plugins/cdh/v5_4_0/resources/hive-site.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch('sahara.plugins.cdh.v5_4_0.edp_engine.EdpOozieEngine')
    def test_get_possible_job_config_java(self, BaseCDHEdpOozieEngine):
        expected_config = {'job_config': {}}
        BaseCDHEdpOozieEngine.get_possible_job_config.return_value = (
            expected_config)
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_JAVA)
        BaseCDHEdpOozieEngine.get_possible_job_config.assert_called_once_with(
            edp.JOB_TYPE_JAVA)
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.plugins.cdh.confighints_helper.'
        'get_possible_mapreduce_config_from',
        return_value={})
    def test_get_possible_job_config_mapreduce(
            self, get_possible_mapreduce_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_MAPREDUCE)
        get_possible_mapreduce_config_from.assert_called_once_with(
            'plugins/cdh/v5_4_0/resources/mapred-site.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.plugins.cdh.confighints_helper.'
        'get_possible_mapreduce_config_from',
        return_value={})
    def test_get_possible_job_config_mapreduce_streaming(
            self, get_possible_mapreduce_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_MAPREDUCE_STREAMING)
        get_possible_mapreduce_config_from.assert_called_once_with(
            'plugins/cdh/v5_4_0/resources/mapred-site.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.plugins.cdh.confighints_helper.get_possible_pig_config_from',
        return_value={})
    def test_get_possible_job_config_pig(self,
                                         get_possible_pig_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_PIG)
        get_possible_pig_config_from.assert_called_once_with(
            'plugins/cdh/v5_4_0/resources/mapred-site.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch('sahara.plugins.cdh.v5_4_0.edp_engine.EdpOozieEngine')
    def test_get_possible_job_config_shell(self, BaseCDHEdpOozieEngine):
        expected_config = {'job_config': {}}
        BaseCDHEdpOozieEngine.get_possible_job_config.return_value = (
            expected_config)
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_SHELL)
        BaseCDHEdpOozieEngine.get_possible_job_config.assert_called_once_with(
            edp.JOB_TYPE_SHELL)
        self.assertEqual(expected_config, actual_config)

    @mock.patch('sahara.plugins.utils.get_config_value_or_default')
    @mock.patch('sahara.plugins.utils.get_instance')
    @mock.patch('sahara.service.edp.spark.engine.'
                'SparkJobEngine.validate_job_execution')
    def test_spark_engine_validate_job_execution(self,
                                                 validate_job_execution,
                                                 get_instance,
                                                 get_config_value_or_default):
        # version unsupported
        cluster = get_cluster(version='5.3.0')
        eng = edp_engine.EdpSparkEngine(cluster)
        self.assertRaises(ex.InvalidDataException,
                          eng.validate_job_execution, cluster,
                          mock.Mock(), mock.Mock())

        # none yarn history server
        cluster = get_cluster()
        eng = edp_engine.EdpSparkEngine(cluster)
        self.assertRaises(pl_ex.InvalidComponentCountException,
                          eng.validate_job_execution, cluster,
                          mock.Mock(), mock.Mock())

        # valid
        cluster = get_cluster()
        yarn_history_node_group = mock.Mock()
        yarn_history_node_group.node_processes = ['SPARK_YARN_HISTORY_SERVER']
        yarn_history_node_group.count = 1
        list.append(cluster.node_groups, yarn_history_node_group)
        eng = edp_engine.EdpSparkEngine(cluster)
        eng.validate_job_execution(cluster, mock.Mock(), mock.Mock())
