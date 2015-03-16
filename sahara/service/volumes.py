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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils as tu

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.i18n import _LW
from sahara.utils import cluster_progress_ops as cpo
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
CONF.import_opt('api_version', 'sahara.utils.openstack.cinder',
                group='cinder')


def _count_instances_to_attach(instances):
    result = 0
    for instance in instances:
        if instance.node_group.volumes_per_node > 0:
            result += 1
    return result


def _count_volumes_to_mount(instances):
    return sum([inst.node_group.volumes_per_node for inst in instances])


def attach_to_instances(instances):
    instances_to_attach = _count_instances_to_attach(instances)
    if instances_to_attach == 0:
        return

    cpo.add_provisioning_step(
        instances[0].cluster_id, _("Attach volumes to instances"),
        instances_to_attach)

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


@cpo.event_wrapper(mark_successful_on_exit=True)
def _attach_volumes_to_node(node_group, instance):
    ctx = context.ctx()
    size = node_group.volumes_size
    volume_type = node_group.volume_type
    devices = []
    for idx in range(1, node_group.volumes_per_node + 1):
        display_name = "volume_" + instance.instance_name + "_" + str(idx)
        device = _create_attach_volume(
            ctx, instance, size, volume_type,
            node_group.volume_local_to_instance, display_name,
            node_group.volumes_availability_zone)
        devices.append(device)
        LOG.debug("Attached volume {device} to instance {uuid}".format(
                  device=device, uuid=instance.instance_id))

    _await_attach_volumes(instance, devices)

    paths = instance.node_group.storage_paths()
    for idx in range(0, instance.node_group.volumes_per_node):
        LOG.debug("Mounting volume {volume} to instance {instance}"
                  .format(volume=device, instance=instance.instance_name))
        _mount_volume(instance, devices[idx], paths[idx])
        LOG.debug("Mounted volume to instance {instance}"
                  .format(instance=instance.instance_name))


def _create_attach_volume(ctx, instance, size, volume_type,
                          volume_local_to_instance, name=None,
                          availability_zone=None):
    if CONF.cinder.api_version == 1:
        kwargs = {'size': size, 'display_name': name}
    else:
        kwargs = {'size': size, 'name': name}

    kwargs['volume_type'] = volume_type
    if availability_zone is not None:
        kwargs['availability_zone'] = availability_zone

    if volume_local_to_instance:
        kwargs['scheduler_hints'] = {'local_to_instance': instance.instance_id}

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
    if len(instances) == 0:
        return

    cpo.add_provisioning_step(
        instances[0].cluster_id,
        _("Mount volumes to instances"), _count_volumes_to_mount(instances))

    with context.ThreadGroup() as tg:
        for instance in instances:
            devices = _find_instance_volume_devices(instance)

            # Since formatting can take several minutes (for large disks) and
            # can be done in parallel, launch one thread per disk.
            for idx in range(0, instance.node_group.volumes_per_node):
                tg.spawn('mount-volume-%d-to-node-%s' %
                         (idx, instance.instance_name),
                         _mount_volume_to_node, instance, idx, devices[idx])


def _find_instance_volume_devices(instance):
    volumes = nova.client().volumes.get_server_volumes(instance.instance_id)
    devices = [volume.device for volume in volumes]
    return devices


@cpo.event_wrapper(mark_successful_on_exit=True)
def _mount_volume_to_node(instance, idx, device):
    LOG.debug("Mounting volume {device} to instance {id}".format(
              device=device, id=instance.instance_id))
    mount_point = instance.node_group.storage_paths()[idx]
    _mount_volume(instance, device, mount_point)
    LOG.debug("Mounted volume to instance {id}".format(
        id=instance.instance_id))


def _mount_volume(instance, device_path, mount_point):
    with instance.remote() as r:
        try:
            # Mount volumes with better performance options:
            # - reduce number of blocks reserved for root to 1%
            # - use 'dir_index' for faster directory listings
            # - use 'extents' to work faster with large files
            # - disable journaling
            # - enable write-back
            # - do not store access time
            fs_opts = '-m 1 -O dir_index,extents,^has_journal'
            mount_opts = '-o data=writeback,noatime,nodiratime'

            r.execute_command('sudo mkdir -p %s' % mount_point)
            r.execute_command('sudo mkfs.ext4 %s %s' % (fs_opts, device_path))
            r.execute_command('sudo mount %s %s %s' %
                              (mount_opts, device_path, mount_point))
        except Exception:
            LOG.error(_LE("Error mounting volume to instance {id}")
                      .format(id=instance.instance_id))
            raise


def detach_from_instance(instance):
    for volume_id in instance.volumes:
        _detach_volume(instance, volume_id)
        _delete_volume(volume_id)


def _detach_volume(instance, volume_id):
    volume = cinder.get_volume(volume_id)
    try:
        LOG.debug("Detaching volume {id}  from instance {instance}".format(
                  id=volume_id, instance=instance.instance_name))
        nova.client().volumes.delete_server_volume(instance.instance_id,
                                                   volume_id)
    except Exception:
        LOG.error(_LE("Can't detach volume {id}").format(id=volume.id))

    detach_timeout = CONF.detach_volume_timeout
    LOG.debug("Waiting {timeout} seconds to detach {id} volume".format(
              timeout=detach_timeout, id=volume_id))
    s_time = tu.utcnow()
    while tu.delta_seconds(s_time, tu.utcnow()) < detach_timeout:
        volume = cinder.get_volume(volume_id)
        if volume.status not in ['available', 'error']:
            context.sleep(2)
        else:
            LOG.debug("Volume {id} has been detached".format(id=volume_id))
            return
    else:
        LOG.warning(_LW("Can't detach volume {volume}. "
                        "Current status of volume: {status}").format(
                            volume=volume_id, status=volume.status))


def _delete_volume(volume_id):
    LOG.debug("Deleting volume {volume}".format(volume=volume_id))
    volume = cinder.get_volume(volume_id)
    try:
        volume.delete()
    except Exception:
        LOG.error(_LE("Can't delete volume {volume}").format(
            volume=volume.id))
