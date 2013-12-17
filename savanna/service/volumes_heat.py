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

from savanna import conductor as c
from savanna.openstack.common import log as logging


conductor = c.API
LOG = logging.getLogger(__name__)


def mount_to_instances(instances):
    for instance in instances:
        _mount_volumes_to_node(instance.node_group, instance)


def _mount_volumes_to_node(node_group, instance, volume_type=None):
    count = node_group.volumes_per_node
    device_paths = _get_device_paths(instance, count)

    for idx in range(0, count):
        LOG.debug("Mounting volume %s to instance %s, type %s" %
                  (device_paths[idx], instance.instance_name, volume_type))
        mount_point = node_group.storage_paths()[idx]
        _mount_volume(instance, device_paths[idx], mount_point)
        LOG.debug("Mounted volume to instance %s" % instance.instance_id)


def _get_device_paths(instance, count):
    code, part_info = instance.remote().execute_command('cat /proc/partitions')

    devices = []

    for line in part_info.split('\n'):
        tokens = line.split()
        if len(tokens) >= 4 and tokens[3] != 'name':
            devices.append('/dev/' + tokens[3])

    LOG.debug('Detected the following drives on the %s: %s' %
              (instance.instance_name, str(devices)))

    if len(devices) <= count:
        raise RuntimeError('There is too small number of devices attached '
                           'to the VM \'%s\' to detect volumes. Expected %i '
                           'devices, found %i: %s' %
                           (instance.instance_name, count, len(devices),
                            str(devices)))

    # we pick devices from the end of the list assuming they were
    # attached the last
    return sorted(devices)[-count:]


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
