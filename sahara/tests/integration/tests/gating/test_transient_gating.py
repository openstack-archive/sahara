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

import time

from oslo_utils import timeutils
import saharaclient.api.base as sab
from testtools import testcase

from sahara.tests.integration.configs import config as cfg
from sahara.tests.integration.tests import base as b
from sahara.tests.integration.tests import edp
from sahara.utils import edp as utils_edp


class TransientGatingTest(edp.EDPTest):
    def get_plugin_config(self):
        return cfg.ITConfig().vanilla_two_config

    def _prepare_test(self):
        self.SKIP_EDP_TEST = self.plugin_config.SKIP_EDP_TEST

    @b.errormsg("Failure while cluster template creation: ")
    def _create_cluster_template(self):
        template = {
            'name': 'test-transient-cluster-template',
            'plugin_config': self.plugin_config,
            'description': 'test cluster template for transient cluster',
            'net_id': self.internal_neutron_net,
            'node_groups': [
                {
                    'name': 'master-node',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['namenode', 'resourcemanager',
                                       'oozie', 'historyserver'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'count': 1
                },
                {
                    'name': 'worker-node',
                    'flavor_id': self.flavor_id,
                    'node_processes': ['datanode', 'nodemanager'],
                    'floating_ip_pool': self.floating_ip_pool,
                    'count': 1
                }
            ],
            'cluster_configs': {
                'HDFS': {
                    'dfs.replication': 1
                },
                'MapReduce': {
                    'mapreduce.tasktracker.map.tasks.maximum': 16,
                    'mapreduce.tasktracker.reduce.tasks.maximum': 16
                },
                'YARN': {
                    'yarn.resourcemanager.scheduler.class':
                    'org.apache.hadoop.yarn.server.resourcemanager.scheduler'
                    '.fair.FairScheduler'
                }
            }
        }
        self.cluster_template_id = self.create_cluster_template(**template)
        self.addCleanup(self.delete_cluster_template, self.cluster_template_id)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        self.cluster_ids = []
        for number_of_cluster in range(3):
            cluster_name = '%s-%d-transient' % (
                self.common_config.CLUSTER_NAME,
                number_of_cluster+1)
            cluster = {
                'name': cluster_name,
                'plugin_config': self.plugin_config,
                'cluster_template_id': self.cluster_template_id,
                'description': 'transient cluster',
                'cluster_configs': {},
                'is_transient': True
            }

            self.cluster_ids.append(self.create_cluster(**cluster))
            self.addCleanup(self.delete_cluster,
                            self.cluster_ids[number_of_cluster])

        for number_of_cluster in range(3):
            self.poll_cluster_state(self.cluster_ids[number_of_cluster])

    @b.errormsg("Failure while transient cluster testing: ")
    def _check_transient(self):
        pig_job_data = self.edp_info.read_pig_example_script()
        pig_lib_data = self.edp_info.read_pig_example_jar()
        job_ids = []
        for cluster_id in self.cluster_ids:
            self.cluster_id = cluster_id
            job_ids.append(self.edp_testing(
                job_type=utils_edp.JOB_TYPE_PIG,
                job_data_list=[{'pig': pig_job_data}],
                lib_data_list=[{'jar': pig_lib_data}]))
        self.poll_jobs_status(job_ids)

        # set timeout in seconds
        timeout = self.common_config.TRANSIENT_CLUSTER_TIMEOUT * 60
        s_time = timeutils.utcnow()
        raise_failure = True
        # wait for cluster deleting
        while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
            try:
                self.sahara.clusters.get(self.cluster_id)
            except sab.APIException as api_ex:
                if 'not found' in api_ex.message:
                    raise_failure = False
                    break
            time.sleep(2)

        if raise_failure:
            self.fail('Transient cluster has not been deleted within %s '
                      'minutes.'
                      % self.common_config.TRANSIENT_CLUSTER_TIMEOUT)

    @testcase.attr('transient')
    def test_transient_gating(self):
        self._prepare_test()
        self._create_cluster_template()
        self._create_cluster()
        self._check_transient()
