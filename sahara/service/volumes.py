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

from oslo.config import cfg
from oslo.utils import timeutils as tu

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.i18n import _LW
from sahara.openstack.common import log as logging
from sahara.utils.openstack import cinder
from sahara.utils.openstack import nova


conductor = c.API
LOG = logging.getLogger(__name__)


opts = [
    cfg.IntOpt(
        'detach_volume_timeout', default=300,
        help='Timeout for detaching volumes from instance (in seconds).')
]

CONF = cfg.CONF
CONF.register_opts(opts)
CONF.import_opt('cinder_api_version', 'sahara.utils.openstack.cinder')


def attach_to_instances(instances):
    with context.ThreadGroup() as tg:
        for instance in instances:
            if instance.node_group.volumes_per_node > 0:
                tg.spawn(
                    'attach-volumes-for-instance-%s' % instance.instance_name,
                    _attach_volumes_to_node, instance.node_group, instance)


def _await_attach_volumes(instance, devices):
    timeout = 10
    step = 2
    while timeout > 0:
        if _count_attached_devices(instance, devices) == len(devices):
            return

        timeout -= step
        context.sleep(step)

    raise ex.SystemError(_("Error attach volume to instance %s") %
                         instance.instance_name)


def _attach_volumes_to_node(node_group, instance):
    ctx = context.ctx()
    size = node_group.volumes_size
    volume_type = node_group.volume_type
    devices = []
    for idx in range(1, node_group.volumes_per_node + 1):
        display_name = "volume_" + instance.instance_name + "_" + str(idx)
        device = _create_attach_volume(
            ctx, instance, size, volume_type, display_name,
            node_group.volumes_availability_zone)
        devices.append(device)
        LOG.debug("Attached volume %s to instance %s" %
                  (device, instance.instance_id))

    _await_attach_volumes(instance, devices)

    for idx in range(0, instance.node_group.volumes_per_node):
        _mount_volume_to_node(instance, idx, devices[idx])


def _create_attach_volume(ctx, instance, size, volume_type, name=None,
                          availability_zone=None):
    if CONF.cinder_api_version == 1:
        kwargs = {'size': size, 'display_name': name}
    else:
        kwargs = {'size': size, 'name': name}

    kwargs['volume_type'] = volume_type
    if availability_zone is not None:
        kwargs['availability_zone'] = availability_zone

    volume = cinder.client().volumes.create(**kwargs)
    conductor.append_volume(ctx, instance, volume.id)

    while volume.status != 'available':
        volume = cinder.get_volume(volume.id)
        if volume.status == 'error':
            raise ex.SystemError(_("Volume %s has error status") % volume.id)

        context.sleep(1)

    resp = nova.client().volumes.create_server_volume(
        instance.instance_id, volume.id, None)
    return resp.device


def _count_attached_devices(instance, devices):
    code, part_info = instance.remote().execute_command('cat /proc/partitions')

    count = 0
    for line in part_info.split('\n')[1:]:
        tokens = line.split()
        if len(tokens) > 3:
            dev = '/dev/' + tokens[3]
            if dev in devices:
                count += 1

    return count


def mount_to_instances(instances):
    with context.ThreadGroup() as tg:
        for instance in instances:
            devices = _find_instance_volume_devices(instance)
            # Since formating can take several minutes (for large disks) and
            # can be done in parallel, launch one thread per disk.
            for idx in range(0, instance.node_group.volumes_per_node):
                tg.spawn('mount-volume-%d-to-node-%s' %
                         (idx, instance.instance_name),
                         _mount_volume_to_node, instance, idx, devices[idx])


def _find_instance_volume_devices(instance):
    volumes = nova.client().volumes.get_server_volumes(instance.instance_id)
    devices = [volume.device for volume in volumes]
    return devices


def _mount_volume_to_node(instance, idx, device):
    LOG.debug("Mounting volume %s to instance %s" %
              (device, instance.instance_name))
    mount_point = instance.node_group.storage_paths()[idx]
    _mount_volume(instance, device, mount_point)
    LOG.debug("Mounted volume to instance %s" % instance.instance_id)


def _mount_volume(instance, device_path, mount_point):
    with instance.remote() as r:
        try:
            r.execute_command('sudo mkdir -p %s' % mount_point)
            r.execute_command('sudo mkfs.ext4 %s' % device_path)
            r.execute_command('sudo mount %s %s' % (device_path, mount_point))
        except Exception:
            LOG.error(_LE("Error mounting volume to instance %s"),
                      instance.instance_id)
            raise


def detach_from_instance(instance):
    for volume_id in instance.volumes:
        _detach_volume(instance, volume_id)
        _delete_volume(volume_id)


def _detach_volume(instance, volume_id):
    volume = cinder.get_volume(volume_id)
    try:
        LOG.debug("Detaching volume %s from instance %s" % (
            volume_id, instance.instance_name))
        nova.client().volumes.delete_server_volume(instance.instance_id,
                                                   volume_id)
    except Exception:
        LOG.exception(_LE("Can't detach volume %s"), volume.id)

    detach_timeout = CONF.detach_volume_timeout
    LOG.debug("Waiting %d seconds to detach %s volume" % (detach_timeout,
                                                          volume_id))
    s_time = tu.utcnow()
    while tu.delta_seconds(s_time, tu.utcnow()) < detach_timeout:
        volume = cinder.get_volume(volume_id)
        if volume.status not in ['available', 'error']:
            context.sleep(2)
        else:
            LOG.debug("Volume %s has been detached" % volume_id)
            return
    else:
        LOG.warn(_LW("Can't detach volume %(volume)s. "
                     "Current status of volume: %(status)s"),
                 {'volume': volume_id, 'status': volume.status})


def _delete_volume(volume_id):
    LOG.debug("Deleting volume %s" % volume_id)
    volume = cinder.get_volume(volume_id)
    try:
        volume.delete()
    except Exception:
        LOG.exception(_LE("Can't delete volume %s"), volume.id)
