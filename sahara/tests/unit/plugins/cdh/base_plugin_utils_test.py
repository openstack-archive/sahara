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

from sahara.i18n import _
from sahara.tests.unit import base as b
from sahara.tests.unit.plugins.cdh import utils as ctu
from sahara.utils import files

CONFIGURATION_SCHEMA = {
    'node_configs': {
        'yarn.scheduler.minimum-allocation-mb': (
            'RESOURCEMANAGER', 'yarn_scheduler_minimum_allocation_mb'),
        'mapreduce.reduce.memory.mb': (
            'YARN_GATEWAY', 'mapreduce_reduce_memory_mb'),
        'mapreduce.map.memory.mb': (
            'YARN_GATEWAY', 'mapreduce_map_memory_mb',),
        'yarn.scheduler.maximum-allocation-mb': (
            'RESOURCEMANAGER', 'yarn_scheduler_maximum_allocation_mb'),
        'yarn.app.mapreduce.am.command-opts': (
            'YARN_GATEWAY', 'yarn_app_mapreduce_am_command_opts'),
        'yarn.nodemanager.resource.memory-mb': (
            'NODEMANAGER', 'yarn_nodemanager_resource_memory_mb'),
        'mapreduce.task.io.sort.mb': (
            'YARN_GATEWAY', 'io_sort_mb'),
        'mapreduce.map.java.opts': (
            'YARN_GATEWAY', 'mapreduce_map_java_opts'),
        'mapreduce.reduce.java.opts': (
            'YARN_GATEWAY', 'mapreduce_reduce_java_opts'),
        'yarn.app.mapreduce.am.resource.mb': (
            'YARN_GATEWAY', 'yarn_app_mapreduce_am_resource_mb')
    },
    'cluster_configs': {
        'dfs.replication': ('HDFS', 'dfs_replication')
    }
}


def get_concrete_cluster():
    cluster = ctu.get_fake_cluster()

    # add configs to cluster
    configs = {"SQOOP": {}, "HUE": {}, "general": {}, "KMS": {}, "HIVE": {},
               "SOLR": {}, "FLUME": {}, "HDFS": {"dfs_replication": 1},
               "KS_INDEXER": {}, "SPARK_ON_YARN": {}, "SENTRY": {}, "YARN": {},
               "ZOOKEEPER": {}, "OOZIE": {}, "HBASE": {}, "IMPALA": {}}
    # cluster is immutable, a work around
    dict.__setitem__(cluster, "cluster_config", configs)

    # add fake remotes to instances
    instances = [i for ng in cluster.node_groups for i in ng.instances]
    for i in instances:
        object.__setattr__(i, 'remote', mock.MagicMock())

    # add cluster_id to each node group
    for ng in cluster.node_groups:
        dict.__setitem__(ng, "cluster_id", ng.cluster.id)

    # add extra config
    dict.__setitem__(cluster, "extra", {})
    return cluster


def get_fake_worker_instances():
    ng = get_concrete_cluster().node_groups[2]
    return ng.instances


class TestPluginUtils(b.SaharaTestCase):

    def setUp(self):
        super(TestPluginUtils, self).setUp()
        self.plug_utils = None

    @mock.patch('sahara.config.CONF.disable_event_log')
    @mock.patch('sahara.plugins.cdh.plugin_utils.'
                'CDHPluginAutoConfigsProvider')
    def test_recommend_configs(self, provider, log_cfg):
        fake_plugin_utils = mock.Mock()
        fake_cluster = mock.Mock()
        self.plug_utils.recommend_configs(
            fake_cluster, fake_plugin_utils, False)
        self.assertEqual([mock.call(CONFIGURATION_SCHEMA,
                                    fake_plugin_utils,
                                    fake_cluster,
                                    False)],
                         provider.call_args_list)

    @mock.patch('sahara.config.CONF.disable_event_log')
    @mock.patch('sahara.plugins.cdh.commands.install_packages')
    def test_install_packages(self, install_packages, log_cfg):
        packages = mock.Mock()
        instances = get_fake_worker_instances()
        self.plug_utils.install_packages(instances, packages)

        calls = [mock.call(i.remote().__enter__(), packages)
                 for i in instances]

        install_packages.assert_has_calls(calls, any_order=False)

    @mock.patch('sahara.config.CONF.disable_event_log')
    @mock.patch('sahara.plugins.cdh.commands.start_agent')
    @mock.patch('sahara.plugins.cdh.commands.configure_agent')
    def test_start_cloudera_agents(self, configure_agent,
                                   start_agent, log_cfg):
        instances = get_fake_worker_instances()

        self.plug_utils.start_cloudera_agents(instances)

        cfg_calls = [mock.call(i.remote().__enter__(), 'manager_inst')
                     for i in instances]
        start_calls = [mock.call(i.remote().__enter__()) for i in instances]

        configure_agent.assert_has_calls(cfg_calls, any_order=False)
        start_agent.assert_has_calls(start_calls, any_order=False)

    @mock.patch('sahara.config.CONF.disable_event_log')
    def test_put_hive_hdfs_xml(self, log_cfg):
        cluster = get_concrete_cluster()
        hive_server = cluster.node_groups[1].instances[0]
        self.plug_utils.put_hive_hdfs_xml(cluster)
        with hive_server.remote() as r:
            calls = [mock.call('sudo su - -c "hadoop fs -mkdir -p'
                               ' /user/hdfs/conf" hdfs'),
                     mock.call('sudo su - -c "hadoop fs -put'
                               ' /etc/hive/conf/hive-site.xml'
                               ' /user/hdfs/conf/hive-site.xml" hdfs')]
            r.execute_command.assert_has_calls(calls, any_order=False)

    @mock.patch('sahara.config.CONF.disable_event_log')
    def test_configure_swift(self, log_cfg):

        cluster = get_concrete_cluster()
        cluster.cluster_config['general']['Enable Swift'] = True
        instances = [i for ng in cluster.node_groups for i in ng.instances]

        self.plug_utils.configure_swift(cluster)
        for i in instances:
            with i.remote() as r:
                cmd = r'ls /usr/lib/hadoop-mapreduce/hadoop-openstack.jar'
                # use any_call because the execute_command has a call:
                # call().__getitem__().__ne__(0) during the method
                r.execute_command.assert_any_call(cmd,
                                                  raise_when_error=False)
                cmd = (r'sudo curl %s'
                       r' -o /usr/lib/hadoop-mapreduce/hadoop-openstack.jar')
                cmd = cmd % self.plug_utils.c_helper.get_swift_lib_url(cluster)
                r.execute_command.call
                r.execute_command.assert_any_call(cmd)

    @mock.patch('sahara.config.CONF.disable_event_log')
    @mock.patch('uuid.uuid4')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('castellan.key_manager.API')
    def test_configure_hive(self, keymanager, cluster_get,
                            cluster_update, uuid4, log_cfg):
        cluster = get_concrete_cluster()
        manager = cluster.node_groups[0].instances[0]
        cluster_get.return_value = cluster
        db_password = 'a8f2939f-ff9f-4659-a333-abc012ee9b2d'
        uuid4.return_value = db_password
        create_db_script = files.get_file_text(
            'plugins/cdh/{version}/resources/create_hive_db.sql'
                                .format(version=self.version))
        create_db_script = create_db_script % db_password

        self.plug_utils.configure_hive(cluster)

        with manager.remote() as r:
            cmd_exe_sql = ('PGPASSWORD=$(sudo head -1'
                           ' /var/lib/cloudera-scm-server-db/data/'
                           'generated_password.txt) psql'
                           ' -U cloudera-scm -h localhost -p 7432 -d scm -f'
                           ' script_to_exec.sql')
            cmd_clean = 'rm script_to_exec.sql'
            self.assertEqual(create_db_script, r.write_file_to.call_args[0][1])
            r.execute_command.assert_has_calls([mock.call(cmd_exe_sql),
                                                mock.call(cmd_clean)])

    @mock.patch('sahara.config.CONF.disable_event_log')
    @mock.patch('sahara.plugins.cdh.commands.is_ubuntu_os')
    @mock.patch('sahara.plugins.cdh.commands.is_centos_os')
    @mock.patch('sahara.plugins.cdh.commands.update_repository')
    @mock.patch('sahara.plugins.cdh.commands.add_apt_key')
    @mock.patch('sahara.plugins.cdh.commands.write_ubuntu_repository')
    @mock.patch('sahara.plugins.cdh.commands.write_centos_repository')
    def test_configure_os(self, write_centos_repository,
                          write_ubuntu_repository, add_apt_key,
                          update_repository, is_centos_os,
                          is_ubuntu_os, log_cfg):
        cluster = get_concrete_cluster()
        ubuntu_instance = cluster.node_groups[2].instances[0]
        centos_instance = cluster.node_groups[2].instances[1]
        instances = [ubuntu_instance, centos_instance]

        is_ubuntu_os.side_effect = \
            lambda r: r is ubuntu_instance.remote().__enter__()
        is_centos_os.side_effect = \
            lambda r: r is centos_instance.remote().__enter__()

        self.plug_utils.configure_os(instances)

        with ubuntu_instance.remote() as r:
            write_ubuntu_repository.assert_has_calls(
                [mock.call(r, self.plug_utils.c_helper.CDH5_UBUNTU_REPO,
                           'cdh'),
                 mock.call(r, self.plug_utils.c_helper.CM5_UBUNTU_REPO,
                           'cm')],
                any_order=False)
            add_apt_key.assert_has_calls(
                [mock.call(r,
                           self.plug_utils.c_helper.
                           DEFAULT_CDH5_UBUNTU_REPO_KEY_URL),
                 mock.call(r,
                           self.plug_utils.c_helper.
                           DEFAULT_CM5_UBUNTU_REPO_KEY_URL)],
                any_order=False)
            update_repository.assert_any_call(r)

        with centos_instance.remote() as r:
            write_centos_repository.assert_has_calls(
                [mock.call(r, self.plug_utils.c_helper.CDH5_CENTOS_REPO,
                           'cdh'),
                 mock.call(r, self.plug_utils.c_helper.CM5_CENTOS_REPO,
                           'cm')],
                any_order=False)
            update_repository.assert_any_call(r)

    @mock.patch('sahara.config.CONF.disable_event_log')
    def test_install_extjs(self, log_cfg):

        cluster = get_concrete_cluster()
        oozie_server = cluster.node_groups[1].instances[0]
        self.plug_utils.install_extjs(cluster)
        with oozie_server.remote() as r:
            calls = [mock.call('ls /var/lib/oozie/ext-2.2',
                               raise_when_error=False),
                     mock.call("curl -L -o '/var/lib/oozie/extjs.zip'"
                               " http://sahara-files.mirantis.com/ext-2.2.zip",
                               run_as_root=True),
                     mock.call('unzip /var/lib/oozie/extjs.zip'
                               ' -d /var/lib/oozie',
                               run_as_root=True)]
            r.execute_command.assert_has_calls(calls, any_order=True)

    @mock.patch('sahara.config.CONF.disable_event_log')
    @mock.patch('sahara.utils.poll_utils.plugin_option_poll')
    @mock.patch('sahara.plugins.cdh.commands.start_cloudera_db')
    @mock.patch('sahara.plugins.cdh.commands.start_manager')
    def test_start_cloudera_manager(self, start_manager, start_cloudera_db,
                                    plugin_option_poll, log_cfg):

        cluster = get_concrete_cluster()
        manager = cluster.node_groups[0].instances[0]

        self.plug_utils.start_cloudera_manager(cluster)
        with manager.remote() as r:
            start_manager.assert_called_once_with(r)
            start_cloudera_db.assert_called_once_with(r)

        call = [cluster,
                self.plug_utils._check_cloudera_manager_started,
                self.plug_utils.c_helper.AWAIT_MANAGER_STARTING_TIMEOUT,
                _("Await starting Cloudera Manager"),
                2, {'manager': manager}]
        plugin_option_poll.assert_called_once_with(*call)


class TestPluginUtilsHigherThanV5(TestPluginUtils):

    @mock.patch('sahara.config.CONF.disable_event_log')
    @mock.patch('uuid.uuid4')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('castellan.key_manager.API')
    def test_configure_sentry(self, keymanager, cluster_get,
                              cluster_update, uuid4, cfg_log):
        cluster = get_concrete_cluster()
        manager = cluster.node_groups[0].instances[0]
        cluster_get.return_value = cluster
        db_password = 'a8f2939f-ff9f-4659-a333-abc012ee9b2d'
        uuid4.return_value = db_password
        create_db_script = files.get_file_text(
            'plugins/cdh/{version}/resources/create_sentry_db.sql'
                                .format(version=self.version))
        create_db_script = create_db_script % db_password

        self.plug_utils.configure_sentry(cluster)

        with manager.remote() as r:
            cmd_exe_sql = ('PGPASSWORD=$(sudo head -1'
                           ' /var/lib/cloudera-scm-server-db/data/'
                           'generated_password.txt) psql'
                           ' -U cloudera-scm -h localhost -p 7432 -d scm -f'
                           ' script_to_exec.sql')
            cmd_clean = 'rm script_to_exec.sql'
            self.assertEqual(create_db_script, r.write_file_to.call_args[0][1])
            r.execute_command.assert_has_calls([mock.call(cmd_exe_sql),
                                                mock.call(cmd_clean)])
