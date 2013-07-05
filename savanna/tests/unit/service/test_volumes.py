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

from cinderclient.v1 import volumes as v
from savanna.db import models as m
from savanna.service import volumes
from savanna.tests.unit import base as models_test_base


class TestAttachVolume(models_test_base.DbTestCase):
    @mock.patch(
        'savanna.utils.remote.BulkInstanceInteropHelper.execute_command')
    def test_mount_volume(self, p_ex_cmd):
        instance = m.Instance(None, None, None)

        p_ex_cmd.return_value = (0, None)
        self.assertIsNone(volumes._mount_volume(instance, '123', '456'))
        self.assertEqual(p_ex_cmd.call_count, 3)
        p_ex_cmd.reset_mock()

        p_ex_cmd.return_value = (1, None)
        self.assertRaises(RuntimeError, volumes._mount_volume,
                          instance, '123', '456')
        self.assertEqual(p_ex_cmd.call_count, 3)

    @mock.patch('cinderclient.v1.volumes.Volume.delete')
    @mock.patch('cinderclient.v1.volumes.Volume.detach')
    @mock.patch('savanna.utils.openstack.cinder.get_volume')
    def test_detach_volumes(self, p_get_volume, p_detach, p_delete):
        instance = m.Instance(None, None, None)
        instance.volumes.append("123")

        p_get_volume.return_value = v.Volume(None, {'id': '123'})
        p_detach.return_value = None
        p_delete.return_value = None
        self.assertIsNone(
            volumes.detach_from_instances([instance]))

        ng = m.NodeGroup(None, None, None, None)
        ng.instances.append(instance)
        cluster = m.Cluster(None, None, None, None)
        cluster.node_groups.append(ng)
        p_delete.side_effect = RuntimeError
        self.assertRaises(RuntimeError, volumes.detach, cluster)

    @mock.patch('savanna.utils.remote.InstanceInteropHelper.execute_command')
    def test_get_free_device_path(self, p_ex_cmd):
        instance = m.Instance(None, None, None)

        p_ex_cmd.return_value = (1, None)
        self.assertRaises(RuntimeError, volumes._get_free_device_path,
                          instance)

        stdout = """major minor  #blocks  name

   8        0  488386584 vda
   8        1     102400 vda1"""

        p_ex_cmd.return_value = (0, stdout)
        self.assertEqual(volumes._get_free_device_path(instance), '/dev/vdb')

        stdout = "major minor  #blocks  name\n"
        for idx in range(0, 26):
            line = "   8        0  488386584 vd" + chr(ord('a') + idx) + '\n'
            stdout += line

        p_ex_cmd.return_value = (0, stdout)
        self.assertRaises(RuntimeError, volumes._get_free_device_path,
                          instance)

    @mock.patch('savanna.service.volumes._mount_volume')
    @mock.patch('savanna.service.volumes._await_attach_volume')
    @mock.patch('savanna.service.volumes._create_attach_volume')
    @mock.patch('savanna.service.volumes._get_free_device_path')
    def test_attach(self, p_dev_path, p_create_attach_vol,
                    p_await, p_mount):
        p_dev_path.return_value = '123'
        p_create_attach_vol.return_value = None
        p_await.return_value = None
        p_mount.return_value = None
        ng = m.NodeGroup(None, None, None, None, volumes_per_node=2,
                         volumes_size=2)
        instance1 = m.Instance(None, None, '123')
        instance2 = m.Instance(None, None, '456')
        instance1.node_group_id = ng.id
        instance2.node_group_id = ng.id
        ng.instances.append(instance1)
        ng.instances.append(instance2)
        cluster = m.Cluster(None, None, None, None)
        cluster.node_groups.append(ng)

        volumes.attach(cluster)
        self.assertEqual(p_create_attach_vol.call_count, 4)
        self.assertEqual(p_await.call_count, 4)
        self.assertEqual(p_mount.call_count, 4)
        self.assertEqual(p_dev_path.call_count, 4)

        p_create_attach_vol.reset_mock()
        p_await.reset_mock()
        p_mount.reset_mock()
        p_dev_path.reset_mock()

        instances = [instance1, instance2]
        volumes.attach_to_instances(instances)

        self.assertEqual(p_create_attach_vol.call_count, 4)
        self.assertEqual(p_await.call_count, 4)
        self.assertEqual(p_mount.call_count, 4)
        self.assertEqual(p_dev_path.call_count, 4)

    @mock.patch('savanna.context.sleep')
    @mock.patch('savanna.service.volumes._get_device_paths')
    def test_await_attach_volume(self, dev_paths, p_sleep):
        dev_paths.return_value = ['/dev/vda', '/dev/vdb']
        p_sleep.return_value = None
        instance = m.Instance(None, None, None)
        self.assertIsNone(volumes._await_attach_volume(instance, '/dev/vdb'))
        self.assertRaises(RuntimeError, volumes._await_attach_volume,
                          instance, '/dev/vdc')
