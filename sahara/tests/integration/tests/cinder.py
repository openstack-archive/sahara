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

from sahara.tests.integration.tests import base


class CinderVolumeTest(base.ITestCase):
    def _get_node_list_with_volumes(self, cluster_info):
        data = self.sahara.clusters.get(cluster_info['cluster_id'])
        node_groups = data.node_groups
        node_list_with_volumes = []
        for node_group in node_groups:
            if node_group['volumes_per_node'] != 0:
                for instance in node_group['instances']:
                    node_with_volume = dict()
                    node_with_volume['node_ip'] = instance['management_ip']
                    node_with_volume['volume_count'] = node_group[
                        'volumes_per_node']
                    node_with_volume['volume_mount_prefix'] = node_group[
                        'volume_mount_prefix']
                    node_list_with_volumes.append(node_with_volume)
        # For example:
        # node_list_with_volumes =  [
        #   {
        #       'volume_mount_prefix': '/volumes/disk',
        #       'volume_count': 2,
        #       'node_ip': '172.18.168.168'
        #   },
        #   {
        #       'volume_mount_prefix': '/volumes/disk',
        #       'volume_count': 2,
        #       'node_ip': '172.18.168.138'
        #   }
        # ]
        return node_list_with_volumes

    @base.skip_test('SKIP_CINDER_TEST', message='Test for Cinder was skipped.')
    def cinder_volume_testing(self, cluster_info):
        node_list_with_volumes = self._get_node_list_with_volumes(cluster_info)
        for node_with_volumes in node_list_with_volumes:
            self.open_ssh_connection(node_with_volumes['node_ip'])
            volume_count_on_node = int(
                self.execute_command(
                    'mount | grep %s | wc -l' % node_with_volumes[
                        'volume_mount_prefix']
                )[1])
            self.assertEqual(
                node_with_volumes['volume_count'], volume_count_on_node,
                'Some volumes was not mounted to node.\n'
                'Expected count of mounted volumes to node is %s.\n'
                'Actual count of mounted volumes to node is %s.'
                % (node_with_volumes['volume_count'], volume_count_on_node)
            )
            self.close_ssh_connection()
