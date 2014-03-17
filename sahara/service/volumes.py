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

import re

from sahara import conductor as c
from sahara import context
from sahara.openstack.common import log as logging
from sahara.utils.openstack import cinder
from sahara.utils.openstack import nova


conductor = c.API
LOG = logging.getLogger(__name__)


def attach(cluster):
    with context.ThreadGroup() as tg:
        for node_group in cluster.node_groups:
            tg.spawn('attach-volumes-for-ng-%s' % node_group.name,
                     attach_to_instances, node_group.instances)


def attach_to_instances(instances):
    with context.ThreadGroup() as tg:
        for instance in instances:
            tg.spawn('attach-volumes-for-instance-%s' % instance.instance_name,
                     _attach_volumes_to_node, instance.node_group, instance)

    mount_to_instances(instances)


def _await_attach_volumes(instance, count_volumes):
    timeout = 10
    step = 2
    while timeout > 0:
        if len(_get_unmounted_devices(instance)) == count_volumes:
            return

        timeout -= step
        context.sleep(step)

    raise RuntimeError("Error attach volume to instance %s" %
                       instance.instance_name)


def _attach_volumes_to_node(node_group, instance, volume_type=None):
    ctx = context.ctx()
    count = node_group.volumes_per_node
    size = node_group.volumes_size
    for idx in range(1, count + 1):
        display_name = "volume_" + instance.instance_name + "_" + str(idx)
        _create_attach_volume(ctx, instance, size, display_name, volume_type)
        LOG.debug("Attach volume to instance %s, type %s" %
                  (instance.instance_id, volume_type))

    _await_attach_volumes(instance, node_group.volumes_per_node)


def _create_attach_volume(ctx, instance, size, display_name=None,
                          volume_type=None):
    volume = cinder.client().volumes.create(size=size,
                                            display_name=display_name,
                                            volume_type=volume_type)
    conductor.append_volume(ctx, instance, volume.id)

    while volume.status != 'available':
        volume = cinder.get_volume(volume.id)
        if volume.status == 'error':
            raise RuntimeError("Volume %s has error status" % volume.id)

        context.sleep(1)

    nova.client().volumes.create_server_volume(instance.instance_id,
                                               volume.id, None)


def _get_unmounted_devices(instance):
    code, part_info = instance.remote().execute_command('cat /proc/partitions')

    devices = []
    partitions = []
    for line in part_info.split('\n')[1:]:
        tokens = line.split()
        if len(tokens) > 3:
            dev = tokens[3]
            if re.search('\d$', dev):
                partitions.append(dev)
            else:
                devices.append(dev)

    # remove devices for which there are partitions
    for partition in partitions:
        match = re.search(r'(.*)\d+', partition)
        if match:
            if match.group(1) in devices:
                devices.remove(match.group(1))

    # add dev prefix
    devices = ['/dev/' + device for device in devices]

    # remove mounted devices
    code, mount_info = instance.remote().execute_command('mount')
    for mount_item in mount_info.split('\n'):
        tokens = mount_item.split(' ')
        if tokens:
            if tokens[0] in devices:
                devices.remove(tokens[0])

    return devices


def mount_to_instances(instances):
    with context.ThreadGroup() as tg:
        for instance in instances:
            tg.spawn('mount-volumes-to-node-%s' % instance.instance_name,
                     _mount_volumes_to_node, instance)


def _mount_volumes_to_node(instance, volume_type=None):
    ng = instance.node_group
    count = ng.volumes_per_node
    device_paths = _get_unmounted_devices(instance)

    for idx in range(0, count):
        LOG.debug("Mounting volume %s to instance %s, type %s" %
                  (device_paths[idx], instance.instance_name, volume_type))
        mount_point = ng.storage_paths()[idx]
        _mount_volume(instance, device_paths[idx], mount_point)
        LOG.debug("Mounted volume to instance %s" % instance.instance_id)


def _mount_volume(instance, device_path, mount_point):
    with instance.remote() as r:
        try:
            r.execute_command('sudo mkdir -p %s' % mount_point)
            r.execute_command('sudo mkfs.ext4 %s' % device_path)
            r.execute_command('sudo mount %s %s' % (device_path, mount_point))
        except Exception:
            LOG.error("Error mounting volume to instance %s" %
                      instance.instance_id)
            raise


def detach_from_instance(instance):
    for volume_id in instance.volumes:
        volume = cinder.get_volume(volume_id)
        try:
            volume.detach()
            volume.delete()
        except Exception:
            LOG.error("Can't detach volume %s" % volume.id)
            raise
