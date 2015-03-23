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
from sahara import exceptions as e
from sahara.plugins import base as pb
from sahara.plugins import exceptions as ex
from sahara.plugins.vanilla import plugin as p
from sahara.plugins.vanilla.v1_2_1 import config_helper as c_h
from sahara.plugins.vanilla.v1_2_1 import mysql_helper as m_h
from sahara.plugins.vanilla.v1_2_1 import versionhandler as v_h
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu
from sahara.utils import edp


conductor = cond.API


class VanillaPluginTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(VanillaPluginTest, self).setUp()
        pb.setup_plugins()
        self.pl = p.VanillaProvider()

    def test_validate(self):
        self.ng = []
        self.ng.append(tu.make_ng_dict("nn", "f1", ["namenode"], 0))
        self.ng.append(tu.make_ng_dict("jt", "f1", ["jobtracker"], 0))
        self.ng.append(tu.make_ng_dict("tt", "f1", ["tasktracker"], 0))
        self.ng.append(tu.make_ng_dict("oozie", "f1", ["oozie"], 0))

        self._validate_case(1, 1, 10, 1)

        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(0, 1, 10, 1)
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(2, 1, 10, 1)

        with testtools.ExpectedException(ex.RequiredServiceMissingException):
            self._validate_case(1, 0, 10, 1)
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 2, 10, 1)

        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 1, 0, 2)
        with testtools.ExpectedException(ex.RequiredServiceMissingException):
            self._validate_case(1, 0, 0, 1)

    def _validate_case(self, *args):
        lst = []
        for i in range(0, len(args)):
            self.ng[i]['count'] = args[i]
            lst.append(self.ng[i])

        cl = tu.create_cluster("cluster1", "tenant1", "vanilla", "1.2.1", lst)

        self.pl.validate(cl)

    def test_get_configs(self):
        cl_configs = self.pl.get_configs("1.2.1")
        for cfg in cl_configs:
            if cfg.config_type is "bool":
                self.assertIsInstance(cfg.default_value, bool)
            elif cfg.config_type is "int":
                try:
                    self.assertIsInstance(cfg.default_value, int)
                except AssertionError:
                    self.assertIsInstance(cfg.default_value, long)
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
        self.assertEqual(['CATALINA_OPTS -Xmx4000m',
                          'HADOOP_DATANODE_OPTS=\\"-Xmx4000m\\"',
                          'HADOOP_JOBTRACKER_OPTS=\\"-Xmx1000m\\"',
                          'HADOOP_NAMENODE_OPTS=\\"-Xmx3000m\\"',
                          'HADOOP_TASKTRACKER_OPTS=\\"-Xmx2000m\\"'],
                         c_h.extract_environment_confs(env_configs))

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

        self.assertEqual([('dfs.replication', 3),
                         ('fs.default.name', 'hdfs://'),
                         ('io.sort.factor', 10),
                         ('mapred.reduce.tasks', 2)],
                         c_h.extract_xml_confs(xml_configs))

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
        self.assertEqual(all_configured, cfg)
        configs['general'].update({'Enable MySQL': False})
        cfg = c_h.generate_cfg_from_general({}, configs, gen_config)
        self.assertEqual({'fs.swift.enabled': True}, cfg)
        configs['general'].update({
            'Enable Swift': False,
            'Enable MySQL': False
        })
        cfg = c_h.generate_cfg_from_general({}, configs, gen_config)
        self.assertEqual({}, cfg)
        configs = {}
        cfg = c_h.generate_cfg_from_general({}, configs, gen_config)
        self.assertEqual(all_configured, cfg)

    def test_get_mysql_configs(self):
        cfg = m_h.get_required_mysql_configs(None, None)
        self.assertEqual(cfg, m_h.get_oozie_mysql_configs())
        cfg = m_h.get_required_mysql_configs("metastore_host", "passwd")
        cfg_to_compare = m_h.get_oozie_mysql_configs()
        cfg_to_compare.update(m_h.get_hive_mysql_configs(
            "metastore_host", "passwd"))
        self.assertEqual(cfg, cfg_to_compare)

    @mock.patch('sahara.conductor.api.LocalApi.cluster_get')
    def test_get_config_value(self, cond_get_cluster):
        cluster = self._get_fake_cluster()
        cond_get_cluster.return_value = cluster

        self.assertEqual(
            'hdfs://inst1:8020',
            c_h.get_config_value('HDFS', 'fs.default.name', cluster))
        self.assertEqual(
            'eggs', c_h.get_config_value('HDFS', 'spam', cluster))
        self.assertEqual(
            30000, c_h.get_config_value('HDFS', 'dfs.safemode.extension'))
        self.assertRaises(e.ConfigurationError,
                          c_h.get_config_value,
                          'MapReduce', 'spam', cluster)

    @mock.patch('sahara.plugins.vanilla.v1_2_1.versionhandler.context')
    @mock.patch('sahara.conductor.api.LocalApi.cluster_update')
    def test_set_cluster_info(self, cond_cluster_update, context_mock):
        cluster = self._get_fake_cluster()
        v_h.VersionHandler()._set_cluster_info(cluster)
        expected_info = {
            'HDFS': {
                'NameNode': 'hdfs://inst1:8020',
                'Web UI': 'http://127.0.0.1:50070'
            },
            'MapReduce': {
                'Web UI': 'http://127.0.0.1:50030',
                'JobTracker': 'inst1:8021'
            },
            'JobFlow': {
                'Oozie': 'http://127.0.0.1:11000'
            }
        }
        cond_cluster_update.assert_called_with(context_mock.ctx(), cluster,
                                               {'info': expected_info})

    def _get_fake_cluster(self):
        class FakeNG(object):
            def __init__(self, name, flavor, processes, count, instances=None,
                         configuration=None, cluster_id=None):
                self.name = name
                self.flavor = flavor
                self.node_processes = processes
                self.count = count
                self.instances = instances or []
                self.ng_configuration = configuration
                self.cluster_id = cluster_id

            def configuration(self):
                return self.ng_configuration

            def storage_paths(self):
                return ['/mnt']

        class FakeCluster(object):
            def __init__(self, name, tenant, plugin, version, node_groups):
                self.name = name
                self.tenant = tenant
                self.plugin = plugin
                self.version = version
                self.node_groups = node_groups

        class FakeInst(object):
            def __init__(self, inst_name, inst_id, management_ip):
                self.instance_name = inst_name
                self.instance_id = inst_id
                self.management_ip = management_ip

            def hostname(self):
                return self.instance_name

        ms_inst = FakeInst('inst1', 'id1', '127.0.0.1')
        wk_inst = FakeInst('inst2', 'id2', '127.0.0.1')

        conf = {
            "MapReduce": {},
            "HDFS": {
                "spam": "eggs"
            },
            "JobFlow": {},
        }

        ng1 = FakeNG('master', 'fl1', ['namenode', 'jobtracker', 'oozie'], 1,
                     [ms_inst], conf, 'id1')
        ng2 = FakeNG('worker', 'fl1', ['datanode', 'tasktracker'], 1,
                     [wk_inst], conf, 'id1')
        return FakeCluster('cl1', 'ten1', 'vanilla', '1.2.1', [ng1, ng2])

    def test_get_hadoop_ssh_keys(self):
        cluster_dict = {
            'name': 'cluster1',
            'plugin_name': 'mock_plugin',
            'hadoop_version': 'mock_version',
            'default_image_id': 'initial',
            'node_groups': [tu.make_ng_dict("ng1", "f1", ["s1"], 1)],
            'extra': {'test': '1'}}

        cluster1 = conductor.cluster_create(context.ctx(), cluster_dict)
        (private_key1, public_key1) = c_h.get_hadoop_ssh_keys(cluster1)

        # should store keys for old cluster
        cluster1 = conductor.cluster_get(context.ctx(), cluster1)
        (private_key2, public_key2) = c_h.get_hadoop_ssh_keys(cluster1)

        self.assertEqual(public_key1, public_key2)
        self.assertEqual(private_key1, private_key2)

        # should generate new keys for new cluster
        cluster_dict.update({'name': 'cluster2'})
        cluster2 = conductor.cluster_create(context.ctx(), cluster_dict)
        (private_key3, public_key3) = c_h.get_hadoop_ssh_keys(cluster2)

        self.assertNotEqual(public_key1, public_key3)
        self.assertNotEqual(private_key1, private_key3)

    @mock.patch('sahara.service.edp.hdfs_helper.create_dir_hadoop1')
    def test_edp_calls_hadoop1_create_dir(self, create_dir):
        cluster_dict = {
            'name': 'cluster1',
            'plugin_name': 'vanilla',
            'hadoop_version': '1.2.1',
            'default_image_id': 'image'}

        cluster = conductor.cluster_create(context.ctx(), cluster_dict)
        plugin = pb.PLUGINS.get_plugin(cluster.plugin_name)
        plugin.get_edp_engine(cluster, edp.JOB_TYPE_PIG).create_hdfs_dir(
            mock.Mock(), '/tmp')

        self.assertEqual(1, create_dir.call_count)
