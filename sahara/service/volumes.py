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
import threading

from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.i18n import _LW
from sahara.plugins import provisioning as plugin_base
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils.openstack import base as b
from sahara.utils.openstack import cinder
from sahara.utils.openstack import nova
from sahara.utils import poll_utils


conductor = c.API
LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('api_version', 'sahara.utils.openstack.cinder',
                group='cinder')


def _get_timeout_for_disk_preparing(cluster):
    configs = cluster.cluster_configs.to_dict()
    option_name = plugin_base.DISKS_PREPARING_TIMEOUT.name
    option_target = plugin_base.DISKS_PREPARING_TIMEOUT.applicable_target
    try:
        return int(configs[option_target][option_name])
    except Exception:
        return int(plugin_base.DISKS_PREPARING_TIMEOUT.default_value)


def _is_xfs_enabled(cluster):
    configs = cluster.cluster_configs.to_dict()
    option_name = plugin_base.XFS_ENABLED.name
    option_target = plugin_base.XFS_ENABLED.applicable_target
    try:
        return bool(configs[option_target][option_name])
    except Exception:
        return bool(plugin_base.XFS_ENABLED.default_value)


def _get_os_distrib(remote):
    return remote.execute_command('lsb_release -is')[1].strip().lower()


def _check_installed_xfs(instance):
    redhat = "rpm -q xfsprogs || yum install -y xfsprogs"
    debian = "dpkg -s xfsprogs || apt-get -y install xfsprogs"

    cmd_map = {
        "centos": redhat,
        "fedora": redhat,
        "redhatenterpriseserver": redhat,
        "ubuntu": debian,
        'debian': debian
    }

    with instance.remote() as r:
        distro = _get_os_distrib(r)
        if not cmd_map.get(distro):
            LOG.warning(
                _LW("Cannot verify installation of XFS tools for "
                    "unknown distro {distro}.").format(distro=distro))
            return False
        try:
            r.execute_command(cmd_map.get(distro), run_as_root=True)
            return True
        except Exception as e:
            LOG.warning(
                _LW("Cannot install xfsprogs: {reason}").format(reason=e))
            return False


def _can_use_xfs(instances):
    cluster = instances[0].cluster
    if not _is_xfs_enabled(cluster):
        return False
    for instance in instances:
        if not _check_installed_xfs(instance):
            return False
    return True


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
        mount_to_instances(instances)
        return

    cpo.add_provisioning_step(
        instances[0].cluster_id, _("Attach volumes to instances"),
        instances_to_attach)

    with context.ThreadGroup() as tg:
        for instance in instances:
            if instance.node_group.volumes_per_node > 0:
                with context.set_current_instance_id(instance.instance_id):
                    tg.spawn(
                        'attach-volumes-for-instance-%s'
                        % instance.instance_name, _attach_volumes_to_node,
                        instance.node_group, instance)

    mount_to_instances(instances)


@poll_utils.poll_status(
    'await_attach_volumes', _("Await for attaching volumes to instances"),
    sleep=2)
def _await_attach_volumes(instance, devices):
    return _count_attached_devices(instance, devices) == len(devices)


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
        LOG.debug("Attached volume {device} to instance".format(device=device))

    _await_attach_volumes(instance, devices)


@poll_utils.poll_status(
    'volume_available_timeout', _("Await for volume become available"),
    sleep=1)
def _await_available(volume):
    volume = cinder.get_volume(volume.id)
    if volume.status == 'error':
        raise ex.SystemError(_("Volume %s has error status") % volume.id)
    return volume.status == 'available'


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

    volume = b.execute_with_retries(cinder.client().volumes.create, **kwargs)
    conductor.append_volume(ctx, instance, volume.id)
    _await_available(volume)

    resp = b.execute_with_retries(nova.client().volumes.create_server_volume,
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

    use_xfs = _can_use_xfs(instances)

    for instance in instances:
        with context.set_current_instance_id(instance.instance_id):
            devices = _find_instance_devices(instance)
            formatted_devices = []
            lock = threading.Lock()
            with context.ThreadGroup() as tg:
                # Since formating can take several minutes (for large disks)
                # and can be done in parallel, launch one thread per disk.
                for device in devices:
                    tg.spawn('format-device-%s' % device, _format_device,
                             instance, device, use_xfs, formatted_devices,
                             lock)

            conductor.instance_update(
                context.current(), instance,
                {"storage_devices_number": len(formatted_devices)})
            for idx, dev in enumerate(formatted_devices):
                _mount_volume_to_node(instance, idx+1, dev, use_xfs)


def _find_instance_devices(instance):
    with instance.remote() as r:
        code, attached_info = r.execute_command(
            "lsblk -r | awk '$6 ~ /disk/ || /part/ {print \"/dev/\" $1}'")
        attached_dev = attached_info.split()
        code, mounted_info = r.execute_command(
            "mount | awk '$1 ~ /^\/dev/ {print $1}'")
        mounted_dev = mounted_info.split()

        # filtering attached devices, that should not be mounted
        for dev in attached_dev[:]:
            idx = re.sub("\D", "", dev)
            if idx:
                if dev in mounted_dev:
                    attached_dev.remove(re.sub("\d", "", dev))
                    attached_dev.remove(dev)

        for dev in attached_dev[:]:
            if re.sub("\D", "", dev):
                if re.sub("\d", "", dev) in attached_dev:
                    attached_dev.remove(dev)

    return attached_dev


@cpo.event_wrapper(mark_successful_on_exit=True)
def _mount_volume_to_node(instance, index, device, use_xfs):
    LOG.debug("Mounting volume {device} to instance".format(device=device))
    mount_point = instance.node_group.volume_mount_prefix + str(index)
    _mount_volume(instance, device, mount_point, use_xfs)
    LOG.debug("Mounted volume to instance")


def _format_device(
        instance, device, use_xfs, formatted_devices=None, lock=None):
    with instance.remote() as r:
        try:
            timeout = _get_timeout_for_disk_preparing(instance.cluster)

            # Format devices with better performance options:
            # - reduce number of blocks reserved for root to 1%
            # - use 'dir_index' for faster directory listings
            # - use 'extents' to work faster with large files
            # - disable journaling
            fs_opts = '-F -m 1 -O dir_index,extents,^has_journal'
            command = 'sudo mkfs.ext4 %s %s' % (fs_opts, device)
            if use_xfs:
                command = 'sudo mkfs.xfs %s' % device
            r.execute_command(command, timeout=timeout)
            if lock:
                with lock:
                    formatted_devices.append(device)
        except Exception as e:
            LOG.warning(
                _LW("Device {dev} cannot be formatted: {reason}").format(
                    dev=device, reason=e))


def _mount_volume(instance, device_path, mount_point, use_xfs):
    with instance.remote() as r:
        try:
            timeout = _get_timeout_for_disk_preparing(instance.cluster)

            # Mount volumes with better performance options:
            # - enable write-back for ext4
            # - do not store access time
            # - disable barrier for xfs

            r.execute_command('sudo mkdir -p %s' % mount_point)
            mount_opts = '-o data=writeback,noatime,nodiratime'
            if use_xfs:
                mount_opts = "-t xfs -o noatime,nodiratime,nobarrier"

            r.execute_command('sudo mount %s %s %s' %
                              (mount_opts, device_path, mount_point),
                              timeout=timeout)
            r.execute_command(
                'sudo sh -c "grep %s /etc/mtab >> /etc/fstab"' % device_path)

        except Exception:
            LOG.error(_LE("Error mounting volume to instance"))
            raise


def detach_from_instance(instance):
    for volume_id in instance.volumes:
        _detach_volume(instance, volume_id)
        _delete_volume(volume_id)


@poll_utils.poll_status(
    'detach_volume_timeout', _("Await for volume become detached"), sleep=2)
def _await_detach(volume_id):
    volume = cinder.get_volume(volume_id)
    if volume.status not in ['available', 'error']:
        return False
    return True


def _detach_volume(instance, volume_id):
    volume = cinder.get_volume(volume_id)
    try:
        LOG.debug("Detaching volume {id} from instance".format(id=volume_id))
        b.execute_with_retries(nova.client().volumes.delete_server_volume,
                               instance.instance_id, volume_id)
    except Exception:
        LOG.error(_LE("Can't detach volume {id}").format(id=volume.id))

    detach_timeout = CONF.timeouts.detach_volume_timeout
    LOG.debug("Waiting {timeout} seconds to detach {id} volume".format(
              timeout=detach_timeout, id=volume_id))
    _await_detach(volume_id)


def _delete_volume(volume_id):
    LOG.debug("Deleting volume {volume}".format(volume=volume_id))
    volume = cinder.get_volume(volume_id)
    try:
        b.execute_with_retries(volume.delete)
    except Exception:
        LOG.error(_LE("Can't delete volume {volume}").format(
            volume=volume.id))
