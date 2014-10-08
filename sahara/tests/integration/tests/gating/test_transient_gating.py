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

from oslo.utils import timeutils
import saharaclient.api.base as sab
from testtools import testcase

from sahara.tests.integration.configs import config as cfg
from sahara.tests.integration.tests import base as b
from sahara.tests.integration.tests import edp
from sahara.utils import edp as utils_edp


class TransientGatingTest(edp.EDPTest):
    def _prepare_test(self):
        self.plugin_config = cfg.ITConfig().vanilla_two_config
        self.SKIP_EDP_TEST = self.plugin_config.SKIP_EDP_TEST
        self.floating_ip_pool = self.common_config.FLOATING_IP_POOL
        self.internal_neutron_net = None
        if self.common_config.NEUTRON_ENABLED:
            self.internal_neutron_net = self.get_internal_neutron_net_id()
            self.floating_ip_pool = (
                self.get_floating_ip_pool_id_for_neutron_net())

        (self.vanilla_two_config.IMAGE_ID,
         self.vanilla_two_config.SSH_USERNAME) = (
            self.get_image_id_and_ssh_username(self.vanilla_two_config))

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
        self.addCleanup(self.delete_objects,
                        cluster_template_id=self.cluster_template_id)

    @b.errormsg("Failure while cluster creation: ")
    def _create_cluster(self):
        cluster_name = '%s-transient' % self.common_config.CLUSTER_NAME
        cluster = {
            'name': cluster_name,
            'plugin_config': self.plugin_config,
            'cluster_template_id': self.cluster_template_id,
            'description': 'transient cluster',
            'cluster_configs': {},
            'is_transient': True
        }
        cluster_id = self.create_cluster(**cluster)
        self.addCleanup(self.delete_objects, cluster_id=cluster_id)
        self.poll_cluster_state(cluster_id)

    @b.errormsg("Failure while transient cluster testing: ")
    def _check_transient(self):
        pig_job_data = self.edp_info.read_pig_example_script()
        pig_lib_data = self.edp_info.read_pig_example_jar()
        job_id = self.edp_testing(job_type=utils_edp.JOB_TYPE_PIG,
                                  job_data_list=[{'pig': pig_job_data}],
                                  lib_data_list=[{'jar': pig_lib_data}])
        self.poll_jobs_status([job_id])

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
