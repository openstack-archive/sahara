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

import nose.plugins.attrib as attrib
import unittest2

from savanna.openstack.common import excutils
from savanna.tests.integration.configs import config as cfg
from savanna.tests.integration.tests import map_reduce
from savanna.tests.integration.tests import scaling
from savanna.tests.integration.tests import swift


class HDPGatingTest(map_reduce.MapReduceTest, swift.SwiftTest,
                    scaling.ScalingTest):

    SKIP_MAP_REDUCE_TEST = cfg.ITConfig().hdp_config.SKIP_MAP_REDUCE_TEST
    SKIP_SWIFT_TEST = cfg.ITConfig().hdp_config.SKIP_SWIFT_TEST
    SKIP_SCALING_TEST = cfg.ITConfig().hdp_config.SKIP_SCALING_TEST

    @attrib.attr(tags='hdp')
    @unittest2.skipIf(cfg.ITConfig().hdp_config.SKIP_ALL_TESTS_FOR_PLUGIN,
                      'All tests for HDP plugin were skipped')
    def test_hdp_plugin_gating(self):

        node_group_template_id_list = []

#-------------------------------CLUSTER CREATION-------------------------------

#-----------------------"tt-dn" node group template creation-------------------

        try:

            node_group_template_tt_dn_id = self.create_node_group_template(
                name='tt-dn',
                plugin_config=self.hdp_config,
                description='test node group template',
                volumes_per_node=0,
                volume_size=0,
                node_processes=['TASKTRACKER', 'DATANODE', 'GANGLIA_MONITOR',
                                'HDFS_CLIENT', 'MAPREDUCE_CLIENT',
                                'AMBARI_AGENT'],
                node_configs={}
            )
            node_group_template_id_list.append(node_group_template_tt_dn_id)

        except Exception as e:

            with excutils.save_and_reraise_exception():

                message = 'Failure while \'tt-dn\' node group ' \
                          'template creation: '
                self.print_error_log(message, e)

#---------------------------Cluster template creation--------------------------

        try:

            cluster_template_id = self.create_cluster_template(
                name='test-cluster-template',
                plugin_config=self.hdp_config,
                description='test cluster template',
                cluster_configs={},
                node_groups=[
                    dict(
                        name='master-node-jt-nn',
                        flavor_id=self.common_config.FLAVOR_ID,
                        node_processes=[
                            'JOBTRACKER', 'NAMENODE', 'SECONDARY_NAMENODE',
                            'GANGLIA_SERVER', 'GANGLIA_MONITOR',
                            'NAGIOS_SERVER', 'AMBARI_SERVER', 'AMBARI_AGENT'
                        ],
                        node_configs={},
                        count=1),
                    dict(
                        name='worker-node-tt-dn',
                        node_group_template_id=node_group_template_tt_dn_id,
                        count=3)
                ]
            )

        except Exception as e:

            with excutils.save_and_reraise_exception():

                self.delete_objects(
                    node_group_template_id_list=node_group_template_id_list
                )

                message = 'Failure while cluster template creation: '
                self.print_error_log(message, e)

#-------------------------------Cluster creation-------------------------------

        try:

            cluster_info = self.create_cluster_and_get_info(
                plugin_config=self.hdp_config,
                cluster_template_id=cluster_template_id,
                description='test cluster',
                cluster_configs={}
            )

        except Exception as e:

            with excutils.save_and_reraise_exception():

                self.delete_objects(
                    self.cluster_id, cluster_template_id,
                    node_group_template_id_list
                )

                message = 'Failure while cluster creation: '
                self.print_error_log(message, e)

#------------------------------MAP REDUCE TESTING------------------------------

        try:

            self._map_reduce_testing(cluster_info)

        except Exception as e:

            with excutils.save_and_reraise_exception():

                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )

                message = 'Failure while Map Reduce testing: '
                self.print_error_log(message, e)

#---------------------------CHECK SWIFT AVAILABILITY---------------------------

        try:

            self._check_swift_availability(cluster_info)

        except Exception as e:

            with excutils.save_and_reraise_exception():

                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )

                message = 'Failure during check of Swift availability: '
                self.print_error_log(message, e)

#--------------------------------CLUSTER SCALING-------------------------------

        change_list = [
            {
                'operation': 'resize',
                'info': ['worker-node-tt-dn', 4]
            },
            {
                'operation': 'add',
                'info': [
                    'new-worker-node-tt-dn', 1, '%s'
                                                % node_group_template_tt_dn_id
                ]
            }
        ]

        try:

            new_cluster_info = self._cluster_scaling(cluster_info, change_list)

        except Exception as e:

            with excutils.save_and_reraise_exception():

                self.delete_objects(
                    cluster_info['cluster_id'], cluster_template_id,
                    node_group_template_id_list
                )

                message = 'Failure while cluster scaling: '
                self.print_error_log(message, e)

        if not self.hdp_config.SKIP_SCALING_TEST:

#-----------------------MAP REDUCE TESTING AFTER SCALING-----------------------

            try:

                self._map_reduce_testing(new_cluster_info)

            except Exception as e:

                with excutils.save_and_reraise_exception():

                    self.delete_objects(
                        new_cluster_info['cluster_id'], cluster_template_id,
                        node_group_template_id_list
                    )

                    message = 'Failure while Map Reduce testing after ' \
                              'cluster scaling: '
                    self.print_error_log(message, e)

#--------------------CHECK SWIFT AVAILABILITY AFTER SCALING--------------------

            try:

                self._check_swift_availability(new_cluster_info)

            except Exception as e:

                with excutils.save_and_reraise_exception():

                    self.delete_objects(
                        new_cluster_info['cluster_id'], cluster_template_id,
                        node_group_template_id_list
                    )

                    message = 'Failure during check of Swift availability ' \
                              'after cluster scaling: '
                    self.print_error_log(message, e)

#----------------------------DELETE CREATED OBJECTS----------------------------

        self.delete_objects(
            cluster_info['cluster_id'], cluster_template_id,
            node_group_template_id_list
        )
