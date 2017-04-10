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
from sahara.i18n import _
from sahara.plugins import provisioning as plugin_base
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils.openstack import base as b
from sahara.utils.openstack import cinder
from sahara.utils.openstack import nova
from sahara.utils import poll_utils


conductor = c.API
LOG = logging.getLogger(__name__)

CONF = cfg.CONF


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
    return remote.get_os_distrib()


def _check_installed_xfs(instance):
    redhat = "rpm -q xfsprogs || yum install -y xfsprogs"
    debian = "dpkg -s xfsprogs || apt-get -y install xfsprogs"

    cmd_map = {
        "centos": redhat,
        "fedora": redhat,
        "redhatenterpriseserver": redhat,
        "redhat": redhat,
        "ubuntu": debian,
        'debian': debian
    }

    with instance.remote() as r:
        distro = _get_os_distrib(r)
        if not cmd_map.get(distro):
            LOG.warning("Cannot verify installation of XFS tools for "
                        "unknown distro {distro}.".format(distro=distro))
            return False
        try:
            r.execute_command(cmd_map.get(distro), run_as_root=True)
            return True
        except Exception as e:
            LOG.warning("Cannot install xfsprogs: {reason}".format(reason=e))
            return False


def _can_use_xfs(instances):
    cluster = instances[0].cluster
    if not _is_xfs_enabled(cluster):
        return False
    for instance in instances:
        if not _check_installed_xfs(instance):
            return False
    return True


def mount_to_instances(instances):
    if len(instances) == 0:
        return

    use_xfs = _can_use_xfs(instances)

    for instance in instances:
        with context.set_current_instance_id(instance.instance_id):
            devices = _find_instance_devices(instance)

            if devices:
                cpo.add_provisioning_step(
                    instance.cluster_id,
                    _("Mount volumes to {inst_name} instance").format(
                        inst_name=instance.instance_name), len(devices))

                formatted_devices = []
                lock = threading.Lock()
                with context.ThreadGroup() as tg:
                    # Since formating can take several minutes (for large
                    # disks) and can be done in parallel, launch one thread
                    # per disk.
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

        # find and ignore Nova config drive
        for label in ("config-2", "CONFIG-2"):
            code, nova_config_drive = r.execute_command(
                "/sbin/blkid -t LABEL=\"%s\" -odevice" % label,
                raise_when_error=False,
                run_as_root=True
            )
            drive_name = nova_config_drive.strip()
            if code == 0 and drive_name in attached_dev:
                attached_dev.remove(drive_name)
                break

    # filtering attached devices, that should not be mounted
    for dev in attached_dev[:]:
        idx = re.sub("\D", "", dev)
        if idx:
            if dev in mounted_dev:
                if re.sub("\d", "", dev) in attached_dev:
                    attached_dev.remove(re.sub("\d", "", dev))
                attached_dev.remove(dev)

    for dev in attached_dev[:]:
        if re.sub("\D", "", dev):
            if re.sub("\d", "", dev) in attached_dev:
                attached_dev.remove(dev)

    attached_dev = [dev for dev in attached_dev if dev not in mounted_dev]

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
                command = 'sudo mkfs.xfs -f %s' % device
            r.execute_command(command, timeout=timeout)
            if lock:
                with lock:
                    formatted_devices.append(device)
        except Exception as e:
            LOG.warning("Device {dev} cannot be formatted: {reason}".format(
                        dev=device, reason=e))
            cpo.add_fail_event(instance, e)


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
            LOG.error("Error mounting volume to instance")
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
        LOG.error("Can't detach volume {id}".format(id=volume.id))

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
        LOG.error("Can't delete volume {volume}".format(volume=volume.id))
