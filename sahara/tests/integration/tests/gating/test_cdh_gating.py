# Copyright (c) 2014 Mirantis Inc.
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

from testtools import testcase

from sahara.tests.integration.configs import config as cfg
from sahara.tests.integration.tests import base as b
from sahara.tests.integration.tests import check_services
from sahara.tests.integration.tests import cinder
from sahara.tests.integration.tests import cluster_configs
from sahara.tests.integration.tests import edp
from sahara.tests.integration.tests import map_reduce
from sahara.tests.integration.tests import scaling
from sahara.tests.integration.tests import swift
from sahara.utils import edp as utils_edp


class CDHGatingTest(check_services.CheckServicesTest,
                    cluster_configs.ClusterConfigTest,
                    map_reduce.MapReduceTest, swift.SwiftTest,
                    scaling.ScalingTest, cinder.CinderVolumeTest, edp.EDPTest):

    cdh_config = cfg.ITConfig().cdh_config
    SKIP_MAP_REDUCE_TEST = cdh_config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = cdh_config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = cdh_config.SKIP_SCALING_TEST
    SKIP_CINDER_TEST = cdh_config.SKIP_CINDER_TEST
    SKIP_EDP_TEST = cdh_config.SKIP_EDP_TEST
    SKIP_CHECK_SERVICES_TEST = cdh_config.SKIP_CHECK_SERVICES_TEST

    def setUp(self):
        super(CDHGatingTest, self).setUp()
        self.cluster_id = None
        self.cluster_template_id = None
        self.services_cluster_template_id = None
        self.flavor_id = self.plugin_config.LARGE_FLAVOR

    def get_plugin_config(self):
        return cfg.ITConfig().cdh_config

    @b.errormsg("Failure while 'nm-dn' node group template creation: ")
    def _create_nm_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-cdh-nm-dn',
            'plugin_config': self.plugin_config,
            'description': 'test node group template for CDH plugin',
            'node_processes': ['YARN_NODEMANAGER', 'HDFS_DATANODE'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_nm_dn_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template, self.ng_tmpl_nm_dn_id)

    @b.errormsg("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        cl_config = {
            'general': {
                'CDH5 repo list URL': self.plugin_config.CDH_REPO_LIST_URL,
                'CM5 repo list URL': self.plugin_config.CM_REPO_LIST_URL,
                'CDH5 repo key URL (for debian-based only)':
                self.plugin_config.CDH_APT_KEY_URL,
                'CM5 repo key URL (for debian-based only)':
                self.plugin_config.CM_APT_KEY_URL,
                'Enable Swift': True
            }
        }
        template = {
            'name': 'test-cluster-template-cdh',
            'plugin_config': self.plugin_config,
            'description': 'test cluster template for CDH plugin',
            'cluster_configs': cl_config,
            'node_groups': [
                {
                    'name': 'manager-node',
                    'flavor_id': self.plugin_config.MANAGERNODE_FLAVOR,
                    'node_processes': ['CLOUDERA_MANAGER'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
                },
                {
                    'name': 'master-node-rm-nn',
                    'flavor_id': self.plugin_config.MANAGERNODE_FLAVOR,
                    'node_processes': ['HDFS_NAMENODE',
                                       'YARN_RESOURCEMANAGER'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
                },
                {
                    'name': 'master-node-oo-hs-snn-hm-hs2',
                    'flavor_id': self.plugin_config.MANAGERNODE_FLAVOR,
                    'node_processes': ['OOZIE_SERVER', 'YARN_JOBHISTORY',
                                       'HDFS_SECONDARYNAMENODE',
                                       'HIVE_METASTORE', 'HIVE_SERVER2'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'auto_security_group': True,
                    'count': 1
                },
                {
                    'name': 'worker-node-nm-dn',
                    'node_group_template_id': self.ng_tmpl_nm_dn_id,
                    'count': 1
                },
            ],
            'net_id': self.internal_neutron_net
        }
        self.cluster_template_id = self.create_cluster_template(**template)
        self.addCleanup(self.delete_cluster_template, self.cluster_template_id)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster_name = '%s-%s' % (self.common_config.CLUSTER_NAME,
                                  self.plugin_config.PLUGIN_NAME)
        cluster = {
            'name': cluster_name,
            'plugin_config': self.plugin_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {
                'HDFS': {
                    'dfs_replication': 1
                }
            }
        }
        self.cluster_id = self.create_cluster(**cluster)
        self.addCleanup(self.delete_cluster, self.cluster_id)
        self.poll_cluster_state(self.cluster_id)
        self.cluster_info = self.get_cluster_info(self.plugin_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg("Failure while 's-nn' node group template creation: ")
    def _create_s_nn_ng_template(self):
        template = {
            'name': 'test-node-group-template-cdh-s-nn',
            'plugin_config': self.cdh_config,
            'description': 'test node group template for CDH plugin',
            'node_processes': ['HDFS_NAMENODE', 'YARN_RESOURCEMANAGER',
                               'YARN_NODEMANAGER', 'HDFS_DATANODE',
                               'HBASE_MASTER', 'CLOUDERA_MANAGER',
                               'ZOOKEEPER_SERVER', 'HBASE_REGIONSERVER',
                               'YARN_JOBHISTORY', 'OOZIE_SERVER',
                               'FLUME_AGENT', 'HIVE_METASTORE',
                               'HIVE_SERVER2', 'HUE_SERVER', 'SENTRY_SERVER',
                               'SOLR_SERVER', 'SQOOP_SERVER',
                               'KEY_VALUE_STORE_INDEXER', 'HIVE_WEBHCAT',
                               'IMPALA_CATALOGSERVER',
                               'SPARK_YARN_HISTORY_SERVER',
                               'IMPALA_STATESTORE', 'IMPALAD'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_s_nn_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template, self.ng_tmpl_s_nn_id)

    @b.errormsg("Failure while 's-dn' node group template creation: ")
    def _create_s_dn_ng_template(self):
        template = {
            'name': 'test-node-group-template-cdh-s-dn',
            'plugin_config': self.cdh_config,
            'description': 'test node group template for CDH plugin',
            'node_processes': ['HDFS_SECONDARYNAMENODE', 'HDFS_DATANODE',
                               'HBASE_REGIONSERVER', 'FLUME_AGENT',
                               'IMPALAD'],
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': True,
            'node_configs': {}
        }
        self.ng_tmpl_s_dn_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template,
                        self.ng_tmpl_s_dn_id)

    @b.errormsg("Failure while services cluster template creation: ")
    def _create_services_cluster_template(self):
        s_cl_config = {
            'general': {
                'CDH5 repo list URL': self.plugin_config.CDH_REPO_LIST_URL,
                'CM5 repo list URL': self.plugin_config.CM_REPO_LIST_URL,
                'CDH5 repo key URL (for debian-based only)':
                self.plugin_config.CDH_APT_KEY_URL,
                'CM5 repo key URL (for debian-based only)':
                self.plugin_config.CM_APT_KEY_URL,
                'Enable Swift': True
            }
        }
        template = {
            'name': 'test-services-cluster-template-cdh',
            'plugin_config': self.plugin_config,
            'description': 'test cluster template for CDH plugin',
            'cluster_configs': s_cl_config,
            'node_groups': [
                {
                    'name': 'worker-node-s-nn',
                    'node_group_template_id': self.ng_tmpl_s_nn_id,
                    'count': 1
                },
                {
                    'name': 'worker-node-s-dn',
                    'node_group_template_id': self.ng_tmpl_s_dn_id,
                    'count': 1
                }
            ],
            'net_id': self.internal_neutron_net
        }
        self.services_cluster_template_id = self.create_cluster_template(
            **template)
        self.addCleanup(self.delete_cluster_template,
                        self.services_cluster_template_id)

    @b.errormsg("Failure while services cluster creation: ")
    def _create_services_cluster(self):
        cluster_name = '%s-%s' % (self.common_config.CLUSTER_NAME,
                                  self.plugin_config.PLUGIN_NAME)
        cluster = {
            'name': cluster_name,
            'plugin_config': self.plugin_config,
            'cluster_template_id': self.services_cluster_template_id,
            'description': 'services test cluster',
            'cluster_configs': {
                'HDFS': {
                    'dfs_replication': 1
                }
            }
        }
        self.cluster_id = self.create_cluster(**cluster)
        self.poll_cluster_state(self.cluster_id)
        self.cluster_info = self.get_cluster_info(self.plugin_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)
        self.addCleanup(self.delete_cluster, self.cluster_id)

    @b.errormsg("Failure while Cinder testing: ")
    def _check_cinder(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing: ")
    def _check_mapreduce(self):
        self.map_reduce_testing(self.cluster_info, check_log=False)

    @b.errormsg("Failure during check of Swift availability: ")
    def _check_swift(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing: ")
    def _check_edp(self):
        self.poll_jobs_status(list(self._run_edp_test()))

    def _run_edp_test(self):
        # check pig
        pig_job = self.edp_info.read_pig_example_script()
        pig_lib = self.edp_info.read_pig_example_jar()
        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_PIG,
            job_data_list=[{'pig': pig_job}],
            lib_data_list=[{'jar': pig_lib}],
            swift_binaries=False,
            hdfs_local_output=True)

        # check mapreduce
        mapreduce_jar = self.edp_info.read_mapreduce_example_jar()
        mapreduce_configs = self.edp_info.mapreduce_example_configs()
        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE,
            job_data_list=[],
            lib_data_list=[{'jar': mapreduce_jar}],
            configs=mapreduce_configs,
            swift_binaries=False,
            hdfs_local_output=True)

        # check mapreduce streaming
        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
            job_data_list=[],
            lib_data_list=[],
            configs=self.edp_info.mapreduce_streaming_configs(),
            swift_binaries=False,
            hdfs_local_output=True)

        # check hive
        yield self.check_edp_hive()

        # check Java
        java_jar = self.edp_info.read_java_example_lib(2)
        java_configs = self.edp_info.java_example_configs(2)
        yield self.edp_testing(
            utils_edp.JOB_TYPE_JAVA,
            job_data_list=[],
            lib_data_list=[{'jar': java_jar}],
            configs=java_configs)

        # check Shell
        shell_script_data = self.edp_info.read_shell_example_script()
        shell_file_data = self.edp_info.read_shell_example_text_file()
        yield self.edp_testing(
            job_type=utils_edp.JOB_TYPE_SHELL,
            job_data_list=[{'script': shell_script_data}],
            lib_data_list=[{'text': shell_file_data}],
            configs=self.edp_info.shell_example_configs())

    @b.errormsg("Failure while check services testing: ")
    def _check_services(self):
        # check HBase
        self.check_hbase_availability(self.cluster_info)
        # check flume
        self.check_flume_availability(self.cluster_info)
        # check sqoop2
        self.check_sqoop2_availability(self.cluster_info)
        # check key value store
        self.check_key_value_store_availability(self.cluster_info)
        # check solr
        self.check_solr_availability(self.cluster_info)
        # check Impala
        self.check_impala_services(self.cluster_info)
        # check sentry
        self.check_sentry_availability(self.cluster_info)

    @b.errormsg("Failure while cluster scaling: ")
    def _check_scaling(self):
        change_list = [
            {
                'operation': 'resize',
                'info': ['worker-node-nm-dn', 1]
            },
            {
                'operation': 'resize',
                'info': ['worker-node-dn', 0]
            },
            {
                'operation': 'resize',
                'info': ['worker-node-nm', 0]
            },
            {
                'operation': 'add',
                'info': [
                    'new-worker-node-nm', 1, '%s' % self.ng_tmpl_nm_id
                ]
            },
            {
                'operation': 'add',
                'info': [
                    'new-worker-node-dn', 1, '%s' % self.ng_tmpl_dn_id
                ]
            }
        ]

        self.cluster_info = self.cluster_scaling(self.cluster_info,
                                                 change_list)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg("Failure while Cinder testing after cluster scaling: ")
    def _check_cinder_after_scaling(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing after cluster scaling: ")
    def _check_mapreduce_after_scaling(self):
        self.map_reduce_testing(self.cluster_info, check_log=False)

    @b.errormsg(
        "Failure during check of Swift availability after cluster scaling: ")
    def _check_swift_after_scaling(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing after cluster scaling: ")
    def _check_edp_after_scaling(self):
        self._check_edp()

    @testcase.skipIf(
        cfg.ITConfig().cdh_config.SKIP_ALL_TESTS_FOR_PLUGIN,
        "All tests for CDH plugin were skipped")
    @testcase.attr('cdh')
    def test_cdh_plugin_gating(self):
        self._success = False
        self._create_nm_dn_ng_template()
        self._create_cluster_template()
        self._create_cluster()
        self._test_event_log(self.cluster_id)

        self._check_cinder()
        self._check_mapreduce()
        self._check_swift()
        self._check_edp()

        if not self.plugin_config.SKIP_SCALING_TEST:
            self._check_scaling()
            self._test_event_log(self.cluster_id)
            self._check_cinder_after_scaling()
            self._check_edp_after_scaling()
            self._check_mapreduce_after_scaling()
            self._check_swift_after_scaling()

        self._success = True

    @testcase.skipIf(
        cfg.ITConfig().cdh_config.SKIP_CHECK_SERVICES_TEST,
        "All services tests for CDH plugin were skipped")
    @testcase.attr('cdh')
    def test_cdh_plugin_services_gating(self):
        self._success = False
        self._create_s_nn_ng_template()
        self._create_s_dn_ng_template()
        self._create_services_cluster_template()
        self._create_services_cluster()
        self._check_services()
        self._success = True

    def print_manager_log(self):
        if not self.cluster_id:
            return

        manager_node = None
        for ng in self.sahara.clusters.get(self.cluster_id).node_groups:
            if 'CLOUDERA_MANAGER' in ng['node_processes']:
                manager_node = ng['instances'][0]['management_ip']
                break

        if not manager_node:
            print("Cloudera Manager node not found")
            return

        self.open_ssh_connection(manager_node)
        try:
            log = self.execute_command('sudo cat /var/log/cloudera-scm-server/'
                                       'cloudera-scm-server.log')[1]
        finally:
            self.close_ssh_connection()

        print("\n\nCLOUDERA MANAGER LOGS\n\n")
        print(log)
        print("\n\nEND OF CLOUDERA MANAGER LOGS\n\n")

    def tearDown(self):
        if not self._success:
            self.print_manager_log()
        super(CDHGatingTest, self).tearDown()
