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

from oslo_utils import excutils

from sahara.tests.integration.tests import base


class ScalingTest(base.ITestCase):
    def _change_node_info_while_ng_adding(self, ngt_id, count, cluster_info):
        cluster_info['node_info']['node_count'] += count
        node_processes = self.sahara.node_group_templates.get(
            ngt_id).node_processes
        if cluster_info['plugin_config'].PROCESS_NAMES['tt'] in node_processes:
            cluster_info['node_info']['tasktracker_count'] += count
        if cluster_info['plugin_config'].PROCESS_NAMES['dn'] in node_processes:
            cluster_info['node_info']['datanode_count'] += count

    def _change_node_info_while_ng_resizing(self, name, count, cluster_info):
        node_groups = self.sahara.clusters.get(
            cluster_info['cluster_id']).node_groups
        for node_group in node_groups:
            if node_group['name'] == name:
                processes = node_group['node_processes']
                old_count = node_group['count']
        cluster_info['node_info']['node_count'] += -old_count + count
        if cluster_info['plugin_config'].PROCESS_NAMES['tt'] in processes:
            cluster_info['node_info']['tasktracker_count'] += (
                -old_count + count
            )
        if cluster_info['plugin_config'].PROCESS_NAMES['dn'] in processes:
            cluster_info['node_info']['datanode_count'] += -old_count + count

    @staticmethod
    def _add_new_field_to_scale_body_while_ng_resizing(
            scale_body, name, count):
        scale_body['resize_node_groups'].append(
            {
                'name': name,
                'count': count
            }
        )

    @staticmethod
    def _add_new_field_to_scale_body_while_ng_adding(
            scale_body, ngt_id, count, name):
        scale_body['add_node_groups'].append(
            {
                'node_group_template_id': ngt_id,
                'count': count,
                'name': name
            }
        )

    @base.skip_test('SKIP_SCALING_TEST',
                    'Test for cluster scaling was skipped.')
    def cluster_scaling(self, cluster_info, change_list):
        scale_body = {'add_node_groups': [], 'resize_node_groups': []}
        for change in change_list:
            if change['operation'] == 'resize':
                node_group_name = change['info'][0]
                node_group_size = change['info'][1]
                self._add_new_field_to_scale_body_while_ng_resizing(
                    scale_body, node_group_name, node_group_size
                )
                self._change_node_info_while_ng_resizing(
                    node_group_name, node_group_size, cluster_info
                )
            if change['operation'] == 'add':
                node_group_name = change['info'][0]
                node_group_size = change['info'][1]
                node_group_id = change['info'][2]
                self._add_new_field_to_scale_body_while_ng_adding(
                    scale_body, node_group_id, node_group_size, node_group_name
                )
                self._change_node_info_while_ng_adding(
                    node_group_id, node_group_size, cluster_info
                )
        scale_body = {key: value for key, value in scale_body.items() if value}
        self.sahara.clusters.scale(cluster_info['cluster_id'], scale_body)
        self.poll_cluster_state(cluster_info['cluster_id'])
        new_node_ip_list = self.get_cluster_node_ip_list_with_node_processes(
            cluster_info['cluster_id']
        )
        try:
            new_node_info = self.get_node_info(new_node_ip_list,
                                               cluster_info['plugin_config'])

        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(
                    '\nFailure during check of node process deployment '
                    'on cluster node: ' + str(e)
                )
        expected_node_info = cluster_info['node_info']
        self.assertEqual(
            expected_node_info, new_node_info,
            'Failure while node info comparison.\n'
            'Expected node info after cluster scaling: %s.\n'
            'Actual node info after cluster scaling: %s.'
            % (expected_node_info, new_node_info)
        )
        return {
            'cluster_id': cluster_info['cluster_id'],
            'node_ip_list': new_node_ip_list,
            'node_info': new_node_info,
            'plugin_config': cluster_info['plugin_config']
        }
