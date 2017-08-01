# Copyright (c) 2017 EasyStack Inc.
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
from oslo_config import cfg

from sahara import exceptions as ex
from sahara.plugins import provisioning as p
from sahara.plugins.vanilla.hadoop2 import config_helper as c_helper
from sahara.tests.unit import base


class TestConfigHelper(base.SaharaTestCase):

    plugin_path = 'sahara.plugins.vanilla.hadoop2.'

    def setUp(self):
        super(TestConfigHelper, self).setUp()
        self.pctx = mock.Mock()
        self.applicable_target = mock.Mock()
        self.name = mock.Mock()
        self.cluster = mock.Mock()
        self.CONF = cfg.CONF
        self.CONF.import_opt("enable_data_locality",
                             "sahara.topology.topology_helper")

    def test_init_env_configs(self):
        ENV_CONFS = {
            "YARN": {
                'ResourceManager Heap Size': 1024,
                'NodeManager Heap Size': 1024
            },
            "HDFS": {
                'NameNode Heap Size': 1024,
                'SecondaryNameNode Heap Size': 1024,
                'DataNode Heap Size': 1024
            },
            "MapReduce": {
                'JobHistoryServer Heap Size': 1024
            },
            "JobFlow": {
                'Oozie Heap Size': 1024
            }
        }
        configs = c_helper.init_env_configs(ENV_CONFS)
        for config in configs:
            self.assertIsInstance(config, p.Config)

    def test_init_general_configs(self):
        sample_configs = [c_helper.ENABLE_SWIFT, c_helper.ENABLE_MYSQL,
                          c_helper.DATANODES_STARTUP_TIMEOUT,
                          c_helper.DATANODES_DECOMMISSIONING_TIMEOUT,
                          c_helper.NODEMANAGERS_DECOMMISSIONING_TIMEOUT]
        self.CONF.enable_data_locality = False
        self.assertEqual(c_helper._init_general_configs(), sample_configs)

        sample_configs.append(c_helper.ENABLE_DATA_LOCALITY)
        self.CONF.enable_data_locality = True
        self.assertEqual(c_helper._init_general_configs(), sample_configs)

    def test_get_config_value(self):
        cluster = mock.Mock()
        ng = mock.Mock()
        ng.configuration.return_value = mock.Mock()
        ng.configuration.return_value.get.return_value = mock.Mock()
        cl = 'test'
        ng.configuration.return_value.get.return_value.get.return_value = cl
        cluster.node_groups = [ng]
        cl_param = c_helper.get_config_value('pctx', 'service',
                                             'name', cluster)
        self.assertEqual(cl, cl_param)

        all_confs = mock.Mock()
        all_confs.applicable_target = 'service'
        all_confs.name = 'name'
        all_confs.default_value = 'default'
        pctx = {'all_confs': [all_confs]}
        value = c_helper.get_config_value(pctx, 'service', 'name')
        self.assertEqual(value, 'default')

        pctx = {'all_confs': []}
        self.assertRaises(ex.NotFoundException, c_helper.get_config_value,
                          pctx, 'service', 'name')

    @mock.patch(plugin_path + 'config_helper.get_config_value')
    def test_is_swift_enabled(self, get_config_value):
        target = c_helper.ENABLE_SWIFT.applicable_target
        name = c_helper.ENABLE_SWIFT.name
        c_helper.is_swift_enabled(self.pctx, self.cluster)
        get_config_value.assert_called_once_with(self.pctx, target,
                                                 name, self.cluster)

    @mock.patch(plugin_path + 'config_helper.get_config_value')
    def test_is_mysql_enabled(self, get_config_value):
        target = c_helper.ENABLE_MYSQL.applicable_target
        name = c_helper.ENABLE_MYSQL.name
        c_helper.is_mysql_enabled(self.pctx, self.cluster)
        get_config_value.assert_called_once_with(self.pctx, target,
                                                 name, self.cluster)

    @mock.patch(plugin_path + 'config_helper.get_config_value')
    def test_is_data_locality_enabled(self, get_config_value):
        self.CONF.enable_data_locality = False
        enabled = c_helper.is_data_locality_enabled(self.pctx, self.cluster)
        self.assertEqual(enabled, False)

        self.CONF.enable_data_locality = True
        target = c_helper.ENABLE_DATA_LOCALITY.applicable_target
        name = c_helper.ENABLE_DATA_LOCALITY.name
        c_helper.is_data_locality_enabled(self.pctx, self.cluster)
        get_config_value.assert_called_once_with(self.pctx, target,
                                                 name, self.cluster)

    def test_get_spark_opt_default(self):
        c_helper.SPARK_CONFS = {'Spark': {
            'OPTIONS': [{'name': 'test_name',
                         'default': 'test'}]}
        }
        opt_name = 'tt'
        default = c_helper._get_spark_opt_default(opt_name)
        self.assertIsNone(default)

        opt_name = 'test_name'
        default = c_helper._get_spark_opt_default(opt_name)
        self.assertEqual(default, 'test')

    def test_generate_spark_env_configs(self):
        configs = 'HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop\n' \
                  'YARN_CONF_DIR=/opt/hadoop/etc/hadoop'
        ret = c_helper.generate_spark_env_configs(self.cluster)
        self.assertEqual(ret, configs)

    @mock.patch('sahara.plugins.utils.get_config_value_or_default')
    def test_generate_spark_executor_classpath(self,
                                               get_config_value_or_default):
        get_config_value_or_default.return_value = None
        path = 'Executor extra classpath'
        ret = c_helper.generate_spark_executor_classpath(self.cluster)
        get_config_value_or_default.assert_called_once_with('Spark',
                                                            path,
                                                            self.cluster)
        self.assertEqual(ret, '\n')

        get_config_value_or_default.return_value = 'test'
        ret = c_helper.generate_spark_executor_classpath(self.cluster)
        self.assertEqual(ret, 'spark.executor.extraClassPath test')

    @mock.patch('sahara.utils.files.get_file_text')
    @mock.patch('sahara.plugins.utils.get_config_value_or_default')
    def test_generate_job_cleanup_config(self,
                                         get_config_value_or_default,
                                         get_file_text):
        cron = 'MINIMUM_CLEANUP_MEGABYTES={minimum_cleanup_megabytes};' + \
               'MINIMUM_CLEANUP_SECONDS={minimum_cleanup_seconds};' + \
               'MAXIMUM_CLEANUP_SECONDS={maximum_cleanup_seconds};'
        script = 'MINIMUM_CLEANUP_MEGABYTES=1;' + \
                 'MINIMUM_CLEANUP_SECONDS=1;' + \
                 'MAXIMUM_CLEANUP_SECONDS=1;'
        job_conf = {'valid': True,
                    'cron': (cron,),
                    'script': script}
        get_file_text.return_value = cron
        get_config_value_or_default.return_value = 1
        ret = c_helper.generate_job_cleanup_config(self.cluster)
        self.assertEqual(get_config_value_or_default.call_count, 3)
        self.assertEqual(get_file_text.call_count, 2)
        self.assertEqual(ret, job_conf)

        job_conf = {'valid': False}
        get_config_value_or_default.return_value = 0
        ret = c_helper.generate_job_cleanup_config(self.cluster)
        self.assertEqual(get_config_value_or_default.call_count, 6)
        self.assertEqual(ret, job_conf)

    @mock.patch('sahara.plugins.utils.get_config_value_or_default')
    def test_get_spark_home(self, get_config_value_or_default):
        get_config_value_or_default.return_value = 1
        self.assertEqual(c_helper.get_spark_home(self.cluster), 1)
        get_config_value_or_default.assert_called_once_with('Spark',
                                                            'Spark home',
                                                            self.cluster)
