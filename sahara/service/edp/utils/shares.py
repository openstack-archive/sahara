# Copyright (c) 2015 Red Hat, Inc.
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

import abc
import collections
import itertools

from oslo_log import log
import six

from sahara import context
from sahara.utils.openstack import manila

LOG = log.getLogger(__name__)


def mount_shares(cluster):
    """Mounts all shares specified for the cluster and any of its node groups.

    - In the event that a specific share is configured for both the cluster and
      a specific node group, configuration at the node group level will be
      ignored.
    - In the event that utilities required to mount the share are not
      already installed on the node, this method may fail if the node cannot
      access the internet.
    - This method will not remove already-mounted shares.
    - This method will not remove or remount (or currently, reconfigure) shares
      already mounted to the desired local mount point.

    :param cluster: The cluster model.
    """

    node_groups = (ng for ng in cluster.node_groups if ng.shares)
    ng_mounts = [_mount(ng, share_config) for ng in node_groups
                 for share_config in ng.shares]
    c_mounts = [_mount(ng, share_config) for ng in cluster.node_groups
                for share_config in cluster.shares or []]

    if not (ng_mounts or c_mounts):
        return

    ng_mounts_by_share_id = _group_mounts_by_share_id(ng_mounts)
    c_mounts_by_share_id = _group_mounts_by_share_id(c_mounts)

    all_share_ids = (set(ng_mounts_by_share_id.keys()) |
                     set(c_mounts_by_share_id.keys()))
    mounts_by_share_id = {
        share_id: c_mounts_by_share_id.get(share_id) or
        ng_mounts_by_share_id[share_id] for share_id in all_share_ids}

    all_mounts = itertools.chain(*mounts_by_share_id.values())
    mounts_by_ng_id = _group_mounts_by_ng_id(all_mounts)

    client = manila.client()
    handlers_by_share_id = {id: _ShareHandler.create_from_id(id, client)
                            for id in all_share_ids}

    for mounts in mounts_by_ng_id.values():
        node_group_shares = _NodeGroupShares(mounts[0].node_group)
        for mount in mounts:
            share_id = mount.share_config['id']
            node_group_shares.add_share(mount.share_config,
                                        handlers_by_share_id[share_id])
        node_group_shares.mount_shares_to_node_group()


def unmount_shares(cluster, unmount_share_list):
    """Unmounts all shares in unmount_share_list on the given cluster

    :param cluster: The cluster model.
    :param unmount_share_list: list of shares to unmount
    """
    client = manila.client()
    unmount_share_ids = (set(s['id'] for s in unmount_share_list))
    handlers_by_share_id = {id: _ShareHandler.create_from_id(id, client)
                            for id in unmount_share_ids}
    for share in unmount_share_list:
        for ng in cluster.node_groups:
            for instance in ng.instances:
                handlers_by_share_id[share['id']].unmount_from_instance(
                    instance.remote(), share)


_mount = collections.namedtuple('Mount', ['node_group', 'share_config'])


def _group_mounts(mounts, grouper):
    result = collections.defaultdict(list)
    for mount in mounts:
        result[grouper(mount)].append(mount)
    return result


def _group_mounts_by_share_id(mounts):
    return _group_mounts(mounts, lambda mount: mount.share_config['id'])


def _group_mounts_by_ng_id(mounts):
    return _group_mounts(mounts, lambda mount: mount.node_group['id'])


class _NodeGroupShares(object):
    """Organizes share mounting for a single node group."""

    _share = collections.namedtuple('Share', ['share_config', 'handler'])

    def __init__(self, node_group):
        self.node_group = node_group
        self.shares = []

    def add_share(self, share_config, handler):
        """Adds a share to mount; add all shares before mounting."""
        self.shares.append(self._share(share_config, handler))

    def mount_shares_to_node_group(self):
        """Mounts all configured shares to the node group."""
        for instance in self.node_group.instances:
            with context.set_current_instance_id(instance.instance_id):
                self._mount_shares_to_instance(instance)

    def _mount_shares_to_instance(self, instance):
        # Note: Additional iteration here is critical: based on
        # experimentation, failure to execute allow_access before spawning
        # the remote results in permission failure.
        for share in self.shares:
            share.handler.allow_access_to_instance(instance,
                                                   share.share_config)
        with instance.remote() as remote:
            share_types = set(type(share.handler) for share in self.shares)
            for share_type in share_types:
                share_type.setup_instance(remote)
            for share in self.shares:
                share.handler.mount_to_instance(remote, share.share_config)


@six.add_metaclass(abc.ABCMeta)
class _ShareHandler(object):
    """Handles mounting of a single share to any number of instances."""

    @classmethod
    def setup_instance(cls, remote):
        """Prepares an instance to mount this type of share."""
        pass

    @classmethod
    def create_from_id(cls, share_id, client):
        """Factory method for creation from a share_id of unknown type."""
        share = manila.get_share(client, share_id,
                                 raise_on_error=True)
        mounter_class = _share_types[share.share_proto]
        return mounter_class(share, client)

    def __init__(self, share, client):
        self.share = share
        self.client = client

    def allow_access_to_instance(self, instance, share_config):
        """Mounts a specific share to a specific instance."""
        access_level = self._get_access_level(share_config)
        accesses = list(filter(lambda x: (x.access_type == 'ip' and
                               x.access_to == instance.internal_ip),
                               self.share.access_list()))
        if accesses:
            access = accesses[0]
            if access.access_level not in ('ro', 'rw'):
                LOG.warning("Unknown permission level {access_level} on share "
                            "id {share_id} for ip {ip}. Leaving pre-existing "
                            "permissions.".format(
                                access_level=access.access_level,
                                share_id=self.share.id,
                                ip=instance.internal_ip))
            elif access.access_level == 'ro' and access_level == 'rw':
                self.share.deny(access.id)
                self.share.allow('ip', instance.internal_ip, access_level)
        else:
            self.share.allow('ip', instance.internal_ip, access_level)

    @abc.abstractmethod
    def mount_to_instance(self, remote, share_info):
        """Mounts the share to the instance as configured."""
        pass

    @abc.abstractmethod
    def unmount_from_instance(self, remote, share_info):
        """Unmounts the share from the instance."""
        pass

    def _get_access_level(self, share_config):
        return share_config.get('access_level', 'rw')

    def _default_mount(self):
        return '/mnt/{0}'.format(self.share.id)

    def _get_path(self, share_info):
        return share_info.get('path', self._default_mount())


class _NFSMounter(_ShareHandler):
    """Handles mounting of a single NFS share to any number of instances."""

    _DEBIAN_INSTALL = "dpkg -s nfs-common || apt-get -y install nfs-common"
    _REDHAT_INSTALL = "rpm -q nfs-utils || yum install -y nfs-utils"

    _NFS_CHECKS = {
        "centos": _REDHAT_INSTALL,
        "fedora": _REDHAT_INSTALL,
        "redhatenterpriseserver": _REDHAT_INSTALL,
        "redhat": _REDHAT_INSTALL,
        "ubuntu": _DEBIAN_INSTALL
    }

    _MKDIR_COMMAND = 'mkdir -p %s'
    _MOUNT_COMMAND = ("mount | grep '%(remote)s' | grep '%(local)s' | "
                      "grep nfs || mount -t nfs %(access_arg)s %(remote)s "
                      "%(local)s")
    _UNMOUNT_COMMAND = ("umount -f %s ")
    _RMDIR_COMMAND = 'rmdir %s'

    @classmethod
    def setup_instance(cls, remote):
        """Prepares an instance to mount this type of share."""
        distro = remote.get_os_distrib()
        if distro in cls._NFS_CHECKS:
            command = cls._NFS_CHECKS[distro]
            remote.execute_command(command, run_as_root=True)
        else:
            LOG.warning("Cannot verify installation of NFS mount tools for "
                        "unknown distro {distro}.".format(distro=distro))

    def mount_to_instance(self, remote, share_info):
        """Mounts the share to the instance as configured."""
        local_path = self._get_path(share_info)
        access_level = self._get_access_level(share_info)
        access_arg = '-w' if access_level == 'rw' else '-r'

        remote.execute_command(self._MKDIR_COMMAND % local_path,
                               run_as_root=True)
        mount_command = self._MOUNT_COMMAND % {
            "remote": self.share.export_location,
            "local": local_path,
            "access_arg": access_arg}
        remote.execute_command(mount_command, run_as_root=True)

    def unmount_from_instance(self, remote, share_info):
        """Unmounts the share from the instance."""
        local_path = self._get_path(share_info)

        unmount_command = self._UNMOUNT_COMMAND % local_path
        rmdir_command = self._RMDIR_COMMAND % local_path
        remote.execute_command(unmount_command, run_as_root=True)
        remote.execute_command(rmdir_command, run_as_root=True)


_share_types = {"NFS": _NFSMounter}
SUPPORTED_SHARE_TYPES = _share_types.keys()


def make_share_path(mount_point, path):
    return "{0}{1}".format(mount_point, path)


def default_mount(share_id):
    client = manila.client()
    return _ShareHandler.create_from_id(share_id, client)._default_mount()


def get_share_path(url, shares):
    # url example: 'manila://ManilaShare-uuid/path_to_file'
    url = six.moves.urllib.parse.urlparse(url)
    # using list() as a python2/3 workaround
    share_list = list(filter(lambda s: s['id'] == url.netloc, shares))
    if not share_list:
        # Share id is not in the share list, let the caller
        # determine a default path if possible
        path = None
    else:
        # We will always select the first one.  Let the
        # caller determine whether duplicates are okay
        mount_point = share_list[0].get('path', None)

        # Do this in two steps instead of passing the default
        # expression to get(), because it's a big side effect
        if mount_point is None:
            # The situation here is that the user specified a
            # share without a path, so the default mnt was used
            # during cluster provisioning.
            mount_point = default_mount(share_list[0]['id'])
        path = make_share_path(mount_point, url.path)
    return path
