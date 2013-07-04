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
import six

from savanna import context
from savanna.openstack.common import log as logging
from savanna.utils.openstack import cinder
from savanna.utils.openstack import nova

LOG = logging.getLogger(__name__)


def attach(cluster):
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            _attach_volumes_to_node(node_group, instance)


def attach_to_instances(instances):
    for instance in instances:
        _attach_volumes_to_node(instance.node_group, instance)


def _await_attach_volume(instance, device_path):
    timeout = 10
    for _ in six.moves.xrange(timeout):
        device_paths = _get_device_paths(instance)
        if device_path in device_paths:
            return
        else:
            context.sleep(1)

    raise RuntimeError("Error attach volume to instance %s" %
                       instance.instance_name)


def _attach_volumes_to_node(node_group, instance, volume_type=None):
    count = node_group.volumes_per_node
    size = node_group.volumes_size
    for idx in range(1, count + 1):
        device_path = _get_free_device_path(instance)
        display_name = "volume_" + instance.instance_name + "_" + str(idx)

        _create_attach_volume(instance, size, device_path, display_name,
                              volume_type)
        _await_attach_volume(instance, device_path)
        LOG.debug("Attach volume to instance %s, type %s" %
                  (instance.instance_id, volume_type))
        mount_point = node_group.storage_paths[idx - 1]
        _mount_volume(instance, device_path, mount_point)
        LOG.debug("Mount volume to instance %s" % instance.instance_id)


def _create_attach_volume(instance, size, device_path, display_name=None,
                          volume_type=None):
    volume = cinder.client().volumes.create(size=size,
                                            display_name=display_name,
                                            volume_type=volume_type)
    instance.volumes.append(volume.id)

    while volume.status != 'available':
        volume = cinder.get_volume(volume.id)
        if volume.status == 'error':
            raise RuntimeError("Volume %s has error status" % volume.id)

        context.sleep(1)

    nova.client().volumes.create_server_volume(instance.instance_id,
                                               volume.id, device_path)


def _get_device_paths(instance):
    code, part_info = instance.remote.execute_command('cat /proc/partitions')
    if code:
        raise RuntimeError("Unable get device paths info")

    out = part_info.split('\n')[1:]
    device_paths = []
    for line in out:
        spl = line.split()
        if len(spl) > 3:
            dev = spl[3]
            if not re.search('\d$', dev):
                device_paths.append('/dev/' + dev)

    return device_paths


def _get_free_device_path(instance):
    device_paths = _get_device_paths(instance)
    for idx in range(0, 26):
        device_path = '/dev/vd' + chr(ord('a') + idx)
        if device_path not in device_paths:
            return device_path

    raise RuntimeError("Unable get free device path")


def _mount_volume(instance, device_path, mount_point):
    codes = []
    with instance.remote as remote:
        code, _ = remote.execute_command('sudo mkdir -p %s' % mount_point)
        codes.append(code)
        code, _ = remote.execute_command('sudo mkfs.ext4 %s' % device_path)
        codes.append(code)
        code, _ = remote.execute_command('sudo mount %s %s' % (device_path,
                                                               mount_point))
        codes.append(code)

    if any(codes):
        raise RuntimeError("Error mounting volume to instance %s" %
                           instance.instance_id)


def detach(cluster):
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            _detach_volume_from_instance(instance)


def detach_from_instances(instances):
    for instance in instances:
        _detach_volume_from_instance(instance)


def _detach_volume_from_instance(instance):
    for volume_id in instance.volumes:
        volume = cinder.get_volume(volume_id)
        try:
            volume.detach()
            volume.delete()
        except Exception:
            LOG.error("Can't detach volume %s" % volume.id)
            raise
