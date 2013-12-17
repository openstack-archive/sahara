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

import mock

from savanna.conductor import resource as r
from savanna import exceptions as ex
from savanna.service import volumes_heat as volumes
from savanna.tests.unit import base as models_test_base


class TestAttachVolume(models_test_base.DbTestCase):
    @mock.patch('savanna.service.instances._get_node_group_image_username')
    def test_mount_volume(self, p_get_username):
        p_get_username.return_value = 'root'

        instance = self._get_instance()
        execute_com = instance.remote().execute_command

        self.assertIsNone(volumes._mount_volume(instance, '123', '456'))
        self.assertEqual(execute_com.call_count, 3)

        execute_com.side_effect = ex.RemoteCommandException('cmd')
        self.assertRaises(ex.RemoteCommandException, volumes._mount_volume,
                          instance, '123', '456')

    def test_get_device_paths(self):

        instance = self._get_instance()
        execute_com = instance.remote().execute_command

        partitions = """major minor  #blocks  name

   7        0   41943040 vdd
   7        1  102400000 vdc
   8        0  976762584 vda
   8        1  842576896 vdb"""

        execute_com.return_value = (0, partitions)

        with self.assertRaises(RuntimeError):
            volumes._get_device_paths(instance, 5)

        paths = volumes._get_device_paths(instance, 3)
        self.assertSequenceEqual(paths, ['/dev/vdb', '/dev/vdc', '/dev/vdd'])

    @mock.patch('savanna.service.volumes_heat._get_device_paths')
    @mock.patch('savanna.service.volumes_heat._mount_volume')
    def test_attach_to_instances(self, p_mount, p_get_paths):
        p_get_paths.return_value = ['/dev/vda, /dev/vdb', '/dev/vdc']
        p_mount.return_value = None

        instance1 = {'instance_id': '123',
                     'instance_name': 'inst_1'}
        instance2 = {'instance_id': '456',
                     'instance_name': 'inst_2'}

        ng = {'volumes_per_node': 2,
              'volumes_size': 2,
              'volume_mount_prefix': '/mnt/vols',
              'instances': [instance1, instance2]}

        cluster = r.ClusterResource({'node_groups': [ng]})

        instances = cluster.node_groups[0].instances
        volumes.mount_to_instances(instances)

        self.assertEqual(p_get_paths.call_count, 2)
        self.assertEqual(p_mount.call_count, 4)

    def _get_instance(self):
        inst_remote = mock.MagicMock()
        inst_remote.execute_command.return_value = 0
        inst_remote.__enter__.return_value = inst_remote

        inst = mock.MagicMock()
        inst.remote.return_value = inst_remote

        return inst
