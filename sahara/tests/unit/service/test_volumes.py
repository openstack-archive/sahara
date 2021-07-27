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

from unittest import mock

from cinderclient.v3 import volumes as vol_v3

from sahara import exceptions as ex
from sahara.service import volumes
from sahara.tests.unit import base


class TestAttachVolume(base.SaharaWithDbTestCase):

    @mock.patch('sahara.service.engine.Engine.get_node_group_image_username')
    def test_mount_volume(self, p_get_username):
        p_get_username.return_value = 'root'

        instance = self._get_instance()
        execute_com = instance.remote().execute_command

        self.assertIsNone(volumes._mount_volume(instance, '123', '456',
                                                False))
        self.assertEqual(3, execute_com.call_count)

        execute_com.side_effect = ex.RemoteCommandException('cmd')
        self.assertRaises(ex.RemoteCommandException, volumes._mount_volume,
                          instance, '123', '456', False)

    @mock.patch('sahara.conductor.manager.ConductorManager.cluster_get')
    @mock.patch('cinderclient.v3.volumes.Volume.delete')
    @mock.patch('cinderclient.v3.volumes.Volume.detach')
    @mock.patch('sahara.utils.openstack.cinder.get_volume')
    def test_detach_volumes_v3(self, p_get_volume, p_detach, p_delete, p_cond):
        class Instance(object):
            def __init__(self):
                self.instance_id = '123454321'
                self.volumes = [123]
                self.instance_name = 'spam'

        instance = Instance()
        p_get_volume.return_value = vol_v3.Volume(None, {'id': '123', 'status':
                                                         'available'})
        p_detach.return_value = None
        p_delete.return_value = None
        self.assertIsNone(
            volumes.detach_from_instance(instance))

    def _get_instance(self):
        inst_remote = mock.MagicMock()
        inst_remote.execute_command.return_value = 0
        inst_remote.__enter__.return_value = inst_remote

        inst = mock.MagicMock()
        inst.remote.return_value = inst_remote

        return inst

    def test_find_instance_volume_devices(self):
        instance = self._get_instance()
        ex_cmd = instance.remote().execute_command

        attached_info = '/dev/vda /dev/vda1 /dev/vdb /dev/vdc'
        mounted_info = '/dev/vda1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info), (2, ""),
                              (2, "")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual(['/dev/vdb', '/dev/vdc'], diff)

        attached_info = '/dev/vda /dev/vda1 /dev/vdb /dev/vdb1 /dev/vdb2'
        mounted_info = '/dev/vda1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info), (2, ""),
                              (2, "")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual(['/dev/vdb'], diff)

        attached_info = '/dev/vda /dev/vda1 /dev/vdb /dev/vdb1 /dev/vdb2'
        mounted_info = '/dev/vda1 /dev/vdb1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info), (2, ""),
                              (2, "")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual(['/dev/vdb2'], diff)

        attached_info = '/dev/vda /dev/vda1 /dev/vdb /dev/vdb1 /dev/vdb2'
        mounted_info = '/dev/vda1 /dev/vdb2'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info), (2, ""),
                              (2, "")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual(['/dev/vdb1'], diff)

        attached_info = '/dev/vda /dev/vda1 /dev/vdb'
        mounted_info = '/dev/vda1 /dev/vdb'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info), (2, ""),
                              (2, "")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual([], diff)

        attached_info = '/dev/vda /dev/vda1 /dev/vdb'
        mounted_info = '/dev/vda1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info),
                              (0, "/dev/vdb")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual([], diff)

        attached_info = '/dev/vda /dev/vda1 /dev/vdb'
        mounted_info = '/dev/vda1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info),
                              (2, ""), (0, "/dev/vdb")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual([], diff)

        attached_info = '/dev/vda /dev/nbd1'
        mounted_info = '/dev/nbd1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info),
                              (2, ""), (2, "")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual(['/dev/vda'], diff)

        attached_info = '/dev/nbd1 /dev/nbd2'
        mounted_info = '/dev/nbd1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info),
                              (2, ""), (2, "")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual(['/dev/nbd2'], diff)

        attached_info = '/dev/nbd1 /dev/nbd2'
        mounted_info = '/dev/nbd1'
        ex_cmd.side_effect = [(0, attached_info), (0, mounted_info),
                              (0, "/dev/nbd2")]

        diff = volumes._find_instance_devices(instance)
        self.assertEqual([], diff)
