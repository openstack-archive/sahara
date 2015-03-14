# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import random
import string
import time
import uuid

import fixtures
import six

from sahara.tests.integration.tests import base as b
from sahara.tests.integration.tests import cinder
from sahara.tests.integration.tests import edp
from sahara.tests.integration.tests import map_reduce
from sahara.tests.integration.tests import scaling
from sahara.tests.integration.tests import swift
from sahara.utils import edp as utils_edp


SERVICES_COUNT_CMD = 'maprcli dashboard info -json'


class MapRGatingTest(map_reduce.MapReduceTest, swift.SwiftTest,
                     scaling.ScalingTest, cinder.CinderVolumeTest,
                     edp.EDPTest):
    def _get_mapr_cluster_info(self):
        return json.loads(self.execute_command(SERVICES_COUNT_CMD)[1])

    def _get_active_count(self, service):
        info = self._get_mapr_cluster_info()
        services = info['data'][0]['services']
        return services[service]['active'] if service in services else -1

    def _get_tasktracker_count(self):
        return self._get_active_count(self._tt_name)

    def _get_datanode_count(self):
        return self._get_active_count('fileserver')

    def await_active_workers_for_namenode(self, node_info, plugin_config):
        tt_count = node_info['tasktracker_count']
        dn_count = node_info['datanode_count']
        self.open_ssh_connection(node_info['namenode_ip'])
        timeout = self.common_config.HDFS_INITIALIZATION_TIMEOUT * 60
        try:
            with fixtures.Timeout(timeout, gentle=True):
                while True:
                    active_tt_count = self._get_tasktracker_count()
                    active_dn_count = self._get_datanode_count()

                    all_tt_started = active_tt_count == tt_count
                    all_dn_started = active_dn_count == dn_count

                    if all_tt_started and all_dn_started:
                        break

                    time.sleep(10)

        except fixtures.TimeoutException:
            self.fail(
                'Tasktracker or datanode cannot be started within '
                '%s minute(s) for namenode.'
                % self.common_config.HDFS_INITIALIZATION_TIMEOUT
            )
        finally:
            self.close_ssh_connection()

    def create_mapr_fs_dir(self, ip, path):
        args = {'user': self.plugin_config.HADOOP_USER, 'path': path}
        self.open_ssh_connection(ip)
        self.execute_command(self._mkdir_cmd % args)
        self.close_ssh_connection()

    def put_file_to_mapr_fs(self, ip, path, data):
        local = '/tmp/%s' % six.text_type(uuid.uuid4())
        args = {
            'user': self.plugin_config.HADOOP_USER,
            'mfs': path,
            'local': local,
        }
        command = 'sudo -u %(user)s hadoop fs -put %(local)s %(mfs)s' % args
        self.open_ssh_connection(ip)
        self.write_file_to(local, data)
        self.execute_command(command)
        self.execute_command('rm -fr %s' % local)
        self.close_ssh_connection()

    @b.skip_test('SKIP_EDP_TEST', 'Test for EDP was skipped.')
    def edp_testing(self, job_type, job_data_list, lib_data_list=None,
                    configs=None, pass_input_output_args=False,
                    swift_binaries=False, hdfs_local_output=False):

        job_data_list = job_data_list or []
        lib_data_list = lib_data_list or []
        configs = configs or {}

        test_id = 'edp-mapr-test-%s' % str(uuid.uuid4())[:8]
        swift = self.connect_to_swift()
        container = test_id
        swift.put_container(container)

        input_folder = '/%s' % test_id
        cldb_ip = self.cluster_info['node_info']['namenode_ip']
        self.create_mapr_fs_dir(cldb_ip, input_folder)

        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.delete_swift_container, swift, container)

        input_data = ''.join(
            random.choice(':' + ' ' + '\n' + string.ascii_lowercase)
            for x in six.moves.range(10000)
        )
        input_file = '%s/input' % input_folder
        self.put_file_to_mapr_fs(cldb_ip, input_file, input_data)

        input_id = None
        output_id = None
        job_binary_list = []
        lib_binary_list = []
        job_binary_internal_list = []

        maprfs_input_url = 'maprfs://%s' % input_file
        maprfs_output_url = 'maprfs://%s/output' % (input_folder + '-out')

        if not utils_edp.compare_job_type(job_type,
                                          utils_edp.JOB_TYPE_JAVA,
                                          utils_edp.JOB_TYPE_SPARK):
            input_id = self._create_data_source(
                'input-%s' % str(uuid.uuid4())[:8], 'maprfs',
                maprfs_input_url)
            output_id = self._create_data_source(
                'output-%s' % str(uuid.uuid4())[:8], 'maprfs',
                maprfs_output_url)

        if job_data_list:
            if swift_binaries:
                self._create_job_binaries(job_data_list,
                                          job_binary_internal_list,
                                          job_binary_list,
                                          swift_connection=swift,
                                          container_name=container)
            else:
                self._create_job_binaries(job_data_list,
                                          job_binary_internal_list,
                                          job_binary_list)

        if lib_data_list:
            if swift_binaries:
                self._create_job_binaries(lib_data_list,
                                          job_binary_internal_list,
                                          lib_binary_list,
                                          swift_connection=swift,
                                          container_name=container)
            else:
                self._create_job_binaries(lib_data_list,
                                          job_binary_internal_list,
                                          lib_binary_list)

        job_id = self._create_job(
            'edp-test-job-%s' % str(uuid.uuid4())[:8], job_type,
            job_binary_list, lib_binary_list)
        if not configs:
            configs = {}

        if utils_edp.compare_job_type(
                job_type, utils_edp.JOB_TYPE_JAVA) and pass_input_output_args:
            self._enable_substitution(configs)
            if "args" in configs:
                configs["args"].extend([maprfs_input_url, maprfs_output_url])
            else:
                configs["args"] = [maprfs_input_url, maprfs_output_url]

        job_execution = self.sahara.job_executions.create(
            job_id, self.cluster_id, input_id, output_id,
            configs=configs)
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.sahara.job_executions.delete,
                            job_execution.id)

        return job_execution.id

    def setUp(self):
        super(MapRGatingTest, self).setUp()
        self.cluster_id = None
        self.cluster_template_id = None
        self._mkdir_cmd = 'sudo -u %(user)s hadoop fs -mkdir -p %(path)s'
        self._tt_name = None
        self._mr_version = None
        self._node_processes = None
        self._master_node_processes = None
        self._worker_node_processes = None

    ng_params = {
    }

    @b.errormsg("Failure while 'single' node group template creation: ")
    def _create_single_ng_template(self):
        template = {
            'name': 'test-node-group-template-mapr-single',
            'plugin_config': self.plugin_config,
            'description': 'test node group template for MapR plugin',
            'node_processes': self._node_processes,
            'floating_ip_pool': self.floating_ip_pool,
            'node_configs': self.ng_params
        }
        self.ng_tmpl_single_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template,
                        self.ng_tmpl_single_id)

    @b.errormsg("Failure while 'master' node group template creation: ")
    def _create_master_ng_template(self):
        plugin_version = self.plugin_config.HADOOP_VERSION.replace('.', '')
        template = {
            'name': 'mapr-%s-master' % plugin_version,
            'plugin_config': self.plugin_config,
            'description': 'Master node group template for MapR plugin',
            'node_processes': self._master_node_processes,
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': False,
            'node_configs': {}
        }
        self.ng_tmpl_master_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template,
                        self.ng_tmpl_master_id)

    @b.errormsg("Failure while 'worker' node group template creation: ")
    def _create_worker_ng_template(self):
        plugin_version = self.plugin_config.HADOOP_VERSION.replace('.', '')
        template = {
            'name': 'mapr-%s-worker' % plugin_version,
            'plugin_config': self.plugin_config,
            'description': 'Worker node group template for MapR plugin',
            'node_processes': self._worker_node_processes,
            'floating_ip_pool': self.floating_ip_pool,
            'auto_security_group': False,
            'node_configs': {}
        }
        self.ng_tmpl_worker_id = self.create_node_group_template(**template)
        self.addCleanup(self.delete_node_group_template,
                        self.ng_tmpl_worker_id)

    @b.errormsg("Failure while cluster template creation: ")
    def _create_master_worker_cluster_template(self):
        plugin_version = self.plugin_config.HADOOP_VERSION.replace('.', '')
        template = {
            'name': 'mapr-%s-master-worker' % plugin_version,
            'plugin_config': self.plugin_config,
            'description': 'test cluster template for MapR plugin',
            'cluster_configs': {
                'Hive': {
                    'Hive Version': '0.13',
                }
            },
            'node_groups': [
                {
                    'name': 'mapr-%s-master' % plugin_version,
                    'node_group_template_id': self.ng_tmpl_master_id,
                    'count': 1
                },
            ],
            'net_id': self.internal_neutron_net
        }
        self.cluster_template_id = self.create_cluster_template(**template)
        self.addCleanup(self.delete_cluster_template,
                        self.cluster_template_id)

    @b.errormsg("Failure while cluster template creation: ")
    def _create_single_node_cluster_template(self):
        template = {
            'name': 'test-cluster-template-mapr-single',
            'plugin_config': self.plugin_config,
            'description': 'test cluster template for MapR plugin',
            'cluster_configs': {
                'Hive': {
                    'Hive Version': '0.13',
                }
            },
            'node_groups': [
                {
                    'name': 'single',
                    'node_group_template_id': self.ng_tmpl_single_id,
                    'count': 1
                },
            ],
            'net_id': self.internal_neutron_net
        }
        self.cluster_template_id = self.create_cluster_template(**template)
        self.addCleanup(self.delete_cluster_template,
                        self.cluster_template_id)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster_name = '%s-%s-v2' % (self.common_config.CLUSTER_NAME,
                                     self.plugin_config.PLUGIN_NAME)
        cluster = {
            'name': cluster_name,
            'plugin_config': self.plugin_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'test cluster',
            'cluster_configs': {}
        }
        cluster_id = self.create_cluster(**cluster)
        self.addCleanup(self.delete_cluster, cluster_id)
        self.poll_cluster_state(cluster_id)
        self.cluster_info = self.get_cluster_info(self.plugin_config)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg("Failure while Cinder testing: ")
    def _check_cinder(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing: ")
    def _check_mapreduce(self):
        self.map_reduce_testing(
            self.cluster_info, script='mapr/map_reduce_test_script.sh')

    @b.errormsg("Failure during check of Swift availability: ")
    def _check_swift(self):
        self.check_swift_availability(
            self.cluster_info, script='mapr/swift_test_script.sh')

    @b.skip_test('SKIP_EDP_TEST',
                 message='Test for EDP was skipped.')
    @b.errormsg("Failure while EDP testing: ")
    def _check_edp(self):
        for edp_job in self._run_edp_tests():
            self.poll_jobs_status([edp_job])

    def _run_edp_tests(self):
        skipped_edp_job_types = self.plugin_config.SKIP_EDP_JOB_TYPES

        if utils_edp.JOB_TYPE_PIG not in skipped_edp_job_types:
            yield self._edp_pig_test()
        if utils_edp.JOB_TYPE_MAPREDUCE not in skipped_edp_job_types:
            yield self._edp_mapreduce_test()
        if utils_edp.JOB_TYPE_MAPREDUCE_STREAMING not in skipped_edp_job_types:
            yield self._edp_mapreduce_streaming_test()
        if utils_edp.JOB_TYPE_JAVA not in skipped_edp_job_types:
            yield self._edp_java_test()

    def _edp_pig_test(self):
        pig_job = self.edp_info.read_pig_example_script()
        pig_lib = self.edp_info.read_pig_example_jar()

        return self.edp_testing(
            job_type=utils_edp.JOB_TYPE_PIG,
            job_data_list=[{'pig': pig_job}],
            lib_data_list=[{'jar': pig_lib}],
            swift_binaries=True
        )

    def _edp_mapreduce_test(self):
        mapreduce_jar = self.edp_info.read_mapreduce_example_jar()
        mapreduce_configs = self.edp_info.mapreduce_example_configs()
        return self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE,
            job_data_list=[],
            lib_data_list=[{'jar': mapreduce_jar}],
            configs=mapreduce_configs,
            swift_binaries=True
        )

    def _edp_mapreduce_streaming_test(self):
        return self.edp_testing(
            job_type=utils_edp.JOB_TYPE_MAPREDUCE_STREAMING,
            job_data_list=[],
            lib_data_list=[],
            configs=self.edp_info.mapreduce_streaming_configs()
        )

    def _edp_java_test(self):
        java_jar = self.edp_info.read_java_example_lib(self._mr_version)
        java_configs = self.edp_info.java_example_configs(self._mr_version)
        return self.edp_testing(
            utils_edp.JOB_TYPE_JAVA,
            job_data_list=[],
            lib_data_list=[{'jar': java_jar}],
            configs=java_configs,
            pass_input_output_args=False
        )

    @b.errormsg("Failure while cluster scaling: ")
    def _check_scaling(self):
        plugin_version = self.plugin_config.HADOOP_VERSION.replace('.', '')
        change_list = [
            {
                'operation': 'add',
                'info': ['mapr-%s-worker' % plugin_version,
                         1, '%s' % self.ng_tmpl_worker_id]
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
        self.map_reduce_testing(self.cluster_info)

    @b.errormsg(
        "Failure during check of Swift availability after cluster scaling: ")
    def _check_swift_after_scaling(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing after cluster scaling: ")
    def _check_edp_after_scaling(self):
        self._check_edp()

    @b.errormsg("Failure while cluster decomission: ")
    def _check_decomission(self):
        plugin_version = self.plugin_config.HADOOP_VERSION.replace('.', '')
        change_list = [
            {
                'operation': 'resize',
                'info': ['mapr-%s-worker' % plugin_version, 1]
            }
        ]

        self.cluster_info = self.cluster_scaling(self.cluster_info,
                                                 change_list)
        self.await_active_workers_for_namenode(self.cluster_info['node_info'],
                                               self.plugin_config)

    @b.errormsg("Failure while Cinder testing after cluster decomission: ")
    def _check_cinder_after_decomission(self):
        self.cinder_volume_testing(self.cluster_info)

    @b.errormsg("Failure while Map Reduce testing after cluster decomission: ")
    def _check_mapreduce_after_decomission(self):
        self.map_reduce_testing(self.cluster_info)

    @b.errormsg("Failure during check of Swift availability after"
                " cluster decomission: ")
    def _check_swift_after_decomission(self):
        self.check_swift_availability(self.cluster_info)

    @b.errormsg("Failure while EDP testing after cluster decomission: ")
    def _check_edp_after_decomission(self):
        self._check_edp()

    def test_mapr_plugin_gating(self):
        self._create_master_ng_template()
        self._create_worker_ng_template()
        self._create_master_worker_cluster_template()
        self._create_cluster()

        self._check_cinder()
        self._check_mapreduce()
        self._check_swift()
        self._check_edp()

        if not self.plugin_config.SKIP_SCALING_TEST:
            self._check_scaling()
            self._check_cinder_after_scaling()
            self._check_mapreduce_after_scaling()
            self._check_swift_after_scaling()
            self._check_edp_after_scaling()

        if not self.plugin_config.SKIP_DECOMISSION_TEST:
            self._check_decomission()
            self._check_cinder_after_decomission()
            self._check_mapreduce_after_decomission()
            self._check_swift_after_decomission()
            self._check_edp_after_decomission()

    def tearDown(self):
        super(MapRGatingTest, self).tearDown()
