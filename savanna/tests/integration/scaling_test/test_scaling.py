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

import telnetlib
import time

from savanna.tests.integration import base
import savanna.tests.integration.configs.parameters as param


class ClusterScalingTest(base.ITestCase):

    def setUp(self):
        super(ClusterScalingTest, self).setUp()

        telnetlib.Telnet(self.host, self.port)

    def create_cluster_for_scaling(self, node_processes):
        cluster_body = self.make_cl_body_node_processes(node_processes)
        cluster_body['name'] = param.CLUSTER_NAME_SCALING

        cluster_id = self.create_cluster_and_get_id(cluster_body)

        return cluster_id

    def implement_scaling(self, cluster_id, scaling_body):
        self.put_object(self.url_cluster_with_slash, cluster_id,
                        scaling_body, 202)

        self.await_cluster_active(cluster_id)

    def implement_scaling_new_node_group_addition(self, cluster_id,
                                                  scaling_map1,
                                                  scaling_map2='',
                                                  multi_scaling=False):
        if multi_scaling:
            self.implement_scaling(cluster_id, {
                'add_node_groups': [
                {
                    'node_group_template_id': scaling_map1['ngt_id'],
                    'count': scaling_map1['node_count'],
                    'name': scaling_map1['ng_name']
                }, {
                    'node_group_template_id': scaling_map1['ngt_id'],
                    'count': scaling_map2['node_count'],
                    'name': scaling_map2['ng_name']
                }
                ]
            })

        else:
            self.implement_scaling(cluster_id, {
                'add_node_groups': [
                {
                    'node_group_template_id': scaling_map1['ngt_id'],
                    'count': scaling_map1['node_count'],
                    'name': scaling_map1['ng_name']
                }
                ]
            })

    def implement_scaling_addition_to_existing_node_group(self, cluster_id,
                                                          scaling_map1,
                                                          scaling_map2='',
                                                          multi_scaling=False):
        if multi_scaling:
            self.implement_scaling(cluster_id, {
                'resize_node_groups': [
                {
                    'name': scaling_map1['ng_name'],
                    'count': scaling_map1['node_count']

                }, {
                    'name': scaling_map2['ng_name'],
                    'count': scaling_map2['node_count']

                }
                ]
            })

        else:
            self.implement_scaling(cluster_id, {
                'resize_node_groups': [
                {
                    'name': scaling_map1['ng_name'],
                    'count': scaling_map1['node_count']

                }
                ]
            })

    def check_cluster_worker_nodes(self, cluster_id):
        ip_instances = self.get_instances_ip_and_node_processes_list(
            cluster_id)

        time.sleep(10)

        try:
            worker_map = self.get_namenode_ip_and_tt_dn_count(ip_instances)
            self.await_active_workers_for_namenode(worker_map)

            return worker_map

        except Exception as e:
            self.fail(str(e))

    def compare_worker_node_count_after_scaling(self,
                                                worker_map,
                                                worker_type,
                                                worker_node_count):
        self.assertEquals(
            worker_map[worker_type], worker_node_count,
            '%s != %s after cluster scaling!' % (worker_type, worker_type))

    def check_cluster_worker_nodes_after_scaling(self,
                                                 cluster_id,
                                                 worker_type,
                                                 scaling_worker_node_count):
        worker_map = self.check_cluster_worker_nodes(cluster_id)
        self.compare_worker_node_count_after_scaling(
            worker_map, worker_type, scaling_worker_node_count)

    def test_scaling_addition_to_existing_ng(self):
        ng_name_for_tt = 'tt'
        tt_count = 1

        ng_name_for_dn = 'dn'
        dn_count = 1
        dn_replication_factor = 3

        cluster_id = self.create_cluster_for_scaling(
            {'JT': 1, 'NN': 1, 'TT': tt_count, 'DN': dn_count})

        try:
            self.implement_scaling_addition_to_existing_node_group(
                cluster_id, {
                    'ng_name': ng_name_for_tt,
                    'node_count': tt_count + 1
                })
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'tasktracker_count', tt_count + 1)

            self.implement_scaling_addition_to_existing_node_group(
                cluster_id, {
                    'ng_name': ng_name_for_dn,
                    'node_count': dn_count + dn_replication_factor
                })
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'datanode_count', dn_count + dn_replication_factor)

            multi_scaling = True
            self.implement_scaling_addition_to_existing_node_group(
                cluster_id, {
                    'ng_name': ng_name_for_tt,
                    'node_count': 0
                },
                {
                    'ng_name': ng_name_for_dn,
                    'node_count': dn_replication_factor
                },
                multi_scaling)
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'tasktracker_count', 0)
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'datanode_count', dn_replication_factor)

        except Exception as e:
            self.fail(str(e))

        finally:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)

    def test_scaling_new_node_group_addition(self):
        ng_name_for_tt = 'ng-tt'
        added_tt_count = 2

        ng_name_for_dn = 'ng-dn'
        added_dn_count = 2
        dn_replication_factor = 3

        cluster_id = self.create_cluster_for_scaling(
            {'JT+NN': 1, 'TT+DN': 1})

        self.create_node_group_templates()

        try:
            self.implement_scaling_new_node_group_addition(
                cluster_id, {
                    'ngt_id': self.id_tt,
                    'node_count': added_tt_count,
                    'ng_name': ng_name_for_tt,

                })
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'tasktracker_count', added_tt_count + 1)

            self.implement_scaling_new_node_group_addition(
                cluster_id, {
                    'ngt_id': self.id_dn,
                    'node_count': added_dn_count + dn_replication_factor,
                    'ng_name': ng_name_for_dn,

                })
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'datanode_count',
                1 + added_dn_count + dn_replication_factor)

            multi_scaling = True
            self.implement_scaling_addition_to_existing_node_group(
                cluster_id, {
                    'ngt_id': self.id_tt,
                    'node_count': 0,
                    'ng_name': ng_name_for_tt,

                }, {
                    'ngt_id': self.id_dn,
                    'node_count': dn_replication_factor,
                    'ng_name': ng_name_for_dn,

                }, multi_scaling)
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'tasktracker_count', 1)
            self.check_cluster_worker_nodes_after_scaling(
                cluster_id, 'datanode_count', 1 + dn_replication_factor)

        except Exception as e:
            self.fail(str(e))

        finally:
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.delete_node_group_templates()
