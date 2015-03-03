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

from cinderclient.v1 import volumes as vol_v1
from cinderclient.v2 import volumes as vol_v2
import mock

from sahara.conductor import resource as r
from sahara import exceptions as ex
from sahara.service import volumes
from sahara.tests.unit import base
from sahara.utils import general as g


class TestAttachVolume(base.SaharaWithDbTestCase):

    @mock.patch('sahara.service.engine.Engine.get_node_group_image_username')
    def test_mount_volume(self, p_get_username):
        p_get_username.return_value = 'root'

        instance = self._get_instance()
        execute_com = instance.remote().execute_command

        self.assertIsNone(volumes._mount_volume(instance, '123', '456'))
        self.assertEqual(execute_com.call_count, 3)

        execute_com.side_effect = ex.RemoteCommandException('cmd')
        self.assertRaises(ex.RemoteCommandException, volumes._mount_volume,
                          instance, '123', '456')

    @mock.patch('sahara.conductor.manager.ConductorManager.cluster_get')
    @mock.patch('cinderclient.v1.volumes.Volume.delete')
    @mock.patch('cinderclient.v1.volumes.Volume.detach')
    @mock.patch('sahara.utils.openstack.cinder.get_volume')
    def test_detach_volumes(self, p_get_volume, p_detach, p_delete, p_cond):
        class Instance(object):
            def __init__(self):
                self.instance_id = '123454321'
                self.volumes = [123]
                self.instance_name = 'spam'

        instance = Instance()
        p_get_volume.return_value = vol_v1.Volume(None, {'id': '123', 'status':
                                                         'available'})
        p_detach.return_value = None
        p_delete.return_value = None
        self.assertIsNone(
            volumes.detach_from_instance(instance))

    @mock.patch('sahara.conductor.manager.ConductorManager.cluster_get')
    @mock.patch('cinderclient.v2.volumes.Volume.delete')
    @mock.patch('cinderclient.v2.volumes.Volume.detach')
    @mock.patch('sahara.utils.openstack.cinder.get_volume')
    def test_detach_volumes_v2(self, p_get_volume, p_detach, p_delete, p_cond):
        class Instance(object):
            def __init__(self):
                self.instance_id = '123454321'
                self.volumes = [123]
                self.instance_name = 'spam'

        instance = Instance()
        p_get_volume.return_value = vol_v2.Volume(None, {'id': '123', 'status':
                                                         'available'})
        p_detach.return_value = None
        p_delete.return_value = None
        self.assertIsNone(
            volumes.detach_from_instance(instance))

    @base.mock_thread_group
    @mock.patch('sahara.service.volumes._mount_volume')
    @mock.patch('sahara.service.volumes._await_attach_volumes')
    @mock.patch('sahara.service.volumes._create_attach_volume')
    @mock.patch('sahara.utils.cluster_progress_ops.add_successful_event')
    @mock.patch('sahara.utils.cluster_progress_ops.update_provisioning_steps')
    @mock.patch('sahara.utils.cluster_progress_ops.add_provisioning_step')
    def test_attach(self, add_step, update_step, add_event,
                    p_create_attach_vol, p_await, p_mount):
        p_create_attach_vol.side_effect = ['/dev/vdb', '/dev/vdc'] * 2
        p_await.return_value = None
        p_mount.return_value = None
        add_event.return_value = None
        update_step.return_value = None
        add_step.return_value = None

        instance1 = {'id': '1',
                     'instance_id': '123',
                     'instance_name': 'inst_1'}

        instance2 = {'id': '2',
                     'instance_id': '456',
                     'instance_name': 'inst_2'}

        ng = {'volumes_per_node': 2,
              'volumes_size': 2,
              'volumes_availability_zone': None,
              'volume_mount_prefix': '/mnt/vols',
              'volume_type': None,
              'name': 'master',
              'cluster_id': '11',
              'instances': [instance1, instance2],
              'volume_local_to_instance': False}

        cluster = r.ClusterResource({'node_groups': [ng]})

        volumes.attach_to_instances(g.get_instances(cluster))
        self.assertEqual(p_create_attach_vol.call_count, 4)
        self.assertEqual(p_await.call_count, 2)
        self.assertEqual(p_mount.call_count, 4)

    @mock.patch('sahara.context.sleep')
    @mock.patch('sahara.service.volumes._count_attached_devices')
    def test_await_attach_volume(self, dev_count, p_sleep):
        dev_count.return_value = 2
        p_sleep.return_value = None
        instance = r.InstanceResource({'instance_id': '123454321',
                                       'instance_name': 'instt'})
        self.assertIsNone(volumes._await_attach_volumes(
            instance, ['/dev/vda', '/dev/vdb']))
        self.assertRaises(ex.SystemError, volumes._await_attach_volumes,
                          instance, ['/dev/vda', '/dev/vdb', '/dev/vdc'])

    def test_count_attached_devices(self):
        partitions = """major minor  #blocks  name

   7        0   41943040 vdd
   7        1  102400000 vdc
   7        1  222222222 vdc1
   8        0  976762584 vda
   8        0  111111111 vda1
   8        1  842576896 vdb"""

        instance = self._get_instance()
        ex_cmd = instance.remote().execute_command
        ex_cmd.side_effect = [(0, partitions)]

        self.assertEqual(volumes._count_attached_devices(
            instance, ['/dev/vdd', '/dev/vdx']), 1)

    def _get_instance(self):
        inst_remote = mock.MagicMock()
        inst_remote.execute_command.return_value = 0
        inst_remote.__enter__.return_value = inst_remote

        inst = mock.MagicMock()
        inst.remote.return_value = inst_remote

        return inst
