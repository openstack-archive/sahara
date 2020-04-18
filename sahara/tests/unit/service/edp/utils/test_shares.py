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


try:
    from manilaclient.common.apiclient import exceptions as manila_ex
except ImportError:
    from manilaclient.openstack.common.apiclient import exceptions as manila_ex
from unittest import mock

from oslo_utils import uuidutils
import testtools

from sahara import exceptions
from sahara.service.edp.utils import shares
from sahara.tests.unit import base

_NAMENODE_IPS = ['192.168.122.3', '192.168.122.4']
_DATANODE_IPS = ['192.168.122.5', '192.168.122.6', '192.168.122.7']


class _FakeShare(object):

    def __init__(self, id='12345678-1234-1234-1234-123456789012',
                 share_proto='NFS',
                 export_location='192.168.122.1:/path',
                 access_list=None):
        self.id = id
        self.share_proto = share_proto
        self.export_location = export_location
        self.allow = mock.Mock()
        self.deny = mock.Mock()
        self.access_list = mock.Mock(return_value=access_list or [])


def _mock_node_group(ips, share_list):
    # Returns a mocked node group and a list of mocked
    # execute_command functions for its instances.

    execute_mocks = [mock.Mock(return_value="centos") for ip in ips]
    get_id = mock.Mock(return_value=uuidutils.generate_uuid())
    instances = [
        mock.Mock(
            internal_ip=ip,
            remote=mock.Mock(
                return_value=mock.Mock(
                    __enter__=mock.Mock(
                        return_value=mock.Mock(
                            execute_command=execute_mocks[index],
                            get_os_distrib=execute_mocks[index])),
                    __exit__=mock.Mock())))
        for index, ip in enumerate(ips)]

    node_group = mock.Mock(instances=instances,
                           shares=share_list,
                           __getitem__=get_id)
    return node_group, execute_mocks


def _setup_calls():
    return [
        mock.call('rpm -q nfs-utils || yum install -y nfs-utils',
                  run_as_root=True)]


def _expected_calls(local_path, remote_path, access_argument):
    return [
        mock.call('mkdir -p %s' % local_path, run_as_root=True),
        mock.call("mount | grep '%(remote_path)s' | grep '%(local_path)s' | "
                  "grep nfs || mount -t nfs %(access_argument)s "
                  "%(remote_path)s %(local_path)s" %
                  {
                      "local_path": local_path,
                      "remote_path": remote_path,
                      "access_argument": access_argument
                  },
                  run_as_root=True)]


class TestShares(base.SaharaTestCase):

    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.openstack.manila.client')
    def test_mount_nfs_shares_to_ng(self, f_manilaclient, f_context):

        share = _FakeShare()
        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(return_value=share)))

        namenode_group, namenode_executors = _mock_node_group(
            _NAMENODE_IPS,
            [{
                'id': '12345678-1234-1234-1234-123456789012',
                'access_level': 'rw',
                'path': '/mnt/localpath'
            }])

        datanode_group, datanode_executors = _mock_node_group(
            _DATANODE_IPS, [])

        cluster = mock.Mock(
            node_groups=[namenode_group, datanode_group], shares=[])

        shares.mount_shares(cluster)

        permissions = [mock.call('ip', ip, 'rw') for ip in _NAMENODE_IPS]
        share.allow.assert_has_calls(permissions, any_order=True)

        for executor in namenode_executors:
            executor.assert_has_calls(
                _setup_calls() +
                _expected_calls('/mnt/localpath', '192.168.122.1:/path', '-w'))
        for executor in datanode_executors:
            self.assertEqual(0, executor.call_count)

    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.openstack.manila.client')
    def test_mount_nfs_shares_to_cluster(self, f_manilaclient, f_context):

        global_share = _FakeShare()
        namenode_only_share = _FakeShare(
            id='DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF',
            export_location='192.168.122.2:/path')
        all_shares = {share.id: share for share in
                      (global_share, namenode_only_share)}

        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(
                    side_effect=lambda x: all_shares[x])))

        namenode_group, namenode_executors = _mock_node_group(
            ['192.168.122.3', '192.168.122.4'],
            [
                {
                    'id': '12345678-1234-1234-1234-123456789012',
                    'access_level': 'rw',
                    'path': '/mnt/localpath'
                },
                {
                    'id': 'DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF'
                }
            ])

        datanode_group, datanode_executors = _mock_node_group(
            ['192.168.122.5', '192.168.122.6', '192.168.122.7'], [])

        cluster = mock.Mock(
            node_groups=[namenode_group, datanode_group],
            shares=[
                {
                    'id': '12345678-1234-1234-1234-123456789012',
                    'access_level': 'ro',
                    'path': '/mnt/somanylocalpaths'
                }
            ])

        shares.mount_shares(cluster)

        all_permissions = [mock.call('ip', ip, 'ro')
                           for ip in _NAMENODE_IPS + _DATANODE_IPS]
        global_share.allow.assert_has_calls(all_permissions, any_order=True)

        namenode_permissions = [mock.call('ip', ip, 'rw')
                                for ip in _NAMENODE_IPS]
        namenode_only_share.allow.assert_has_calls(namenode_permissions,
                                                   any_order=True)

        for executor in namenode_executors:
            executor.assert_has_calls(
                _setup_calls() +
                _expected_calls('/mnt/somanylocalpaths',
                                '192.168.122.1:/path', '-r') +
                _expected_calls('/mnt/DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF',
                                '192.168.122.2:/path', '-w'),
                any_order=True)
            self.assertEqual(6, executor.call_count)

        for executor in datanode_executors:
            executor.assert_has_calls(
                _setup_calls() +
                _expected_calls('/mnt/somanylocalpaths',
                                '192.168.122.1:/path', '-r'))
            self.assertEqual(4, executor.call_count)

    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.openstack.manila.client')
    def test_share_does_not_exist(self, f_manilaclient, f_context):

        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(
                    side_effect=manila_ex.NotFound)))

        namenode_group, namenode_executors = _mock_node_group(
            ['192.168.122.3', '192.168.122.4'],
            [
                {
                    'id': '12345678-1234-1234-1234-123456789012',
                    'access_level': 'rw',
                    'path': '/mnt/localpath'
                },
                {
                    'id': 'DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF'
                }
            ])

        datanode_group, datanode_executors = _mock_node_group(
            ['192.168.122.5', '192.168.122.6', '192.168.122.7'], [])

        cluster = mock.Mock(
            node_groups=[namenode_group, datanode_group],
            shares=[
                {
                    'id': '12345678-1234-1234-1234-123456789012',
                    'access_level': 'ro',
                    'path': '/mnt/somanylocalpaths'
                }
            ])

        with testtools.ExpectedException(exceptions.NotFoundException):
            shares.mount_shares(cluster)

    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.openstack.manila.client')
    def test_acl_exists_unexpected_type(self, f_manilaclient, f_context):

        share = _FakeShare(access_list=[mock.Mock(
            access_level='wat', access_to=ip, access_type='ip')
            for ip in _NAMENODE_IPS])
        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(return_value=share)))

        namenode_group, namenode_executors = _mock_node_group(
            _NAMENODE_IPS,
            [{
                'id': '12345678-1234-1234-1234-123456789012',
                'access_level': 'rw',
                'path': '/mnt/localpath'
            }])

        datanode_group, datanode_executors = _mock_node_group(
            _DATANODE_IPS, [])

        cluster = mock.Mock(
            node_groups=[namenode_group, datanode_group], shares=[])

        shares.mount_shares(cluster)

        self.assertEqual(0, share.allow.call_count)

        for executor in namenode_executors:
            executor.assert_has_calls(
                _setup_calls() +
                _expected_calls('/mnt/localpath', '192.168.122.1:/path', '-w'))

        for executor in datanode_executors:
            self.assertEqual(0, executor.call_count)

    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.openstack.manila.client')
    def test_acl_exists_no_recreate(self, f_manilaclient, f_context):

        share = _FakeShare(access_list=[mock.Mock(
            access_level='rw', access_to=ip, access_type='ip')
            for ip in _NAMENODE_IPS])
        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(return_value=share)))

        namenode_group, namenode_executors = _mock_node_group(
            _NAMENODE_IPS,
            [{
                'id': '12345678-1234-1234-1234-123456789012',
                'access_level': 'ro',
                'path': '/mnt/localpath'
            }])

        datanode_group, datanode_executors = _mock_node_group(
            _DATANODE_IPS, [])

        cluster = mock.Mock(
            node_groups=[namenode_group, datanode_group], shares=[])

        shares.mount_shares(cluster)

        self.assertEqual(0, share.allow.call_count)

        for executor in namenode_executors:
            executor.assert_has_calls(
                _setup_calls() +
                _expected_calls('/mnt/localpath', '192.168.122.1:/path', '-r'))

        for executor in datanode_executors:
            self.assertEqual(0, executor.call_count)

    @mock.patch('sahara.context.set_current_instance_id')
    @mock.patch('sahara.utils.openstack.manila.client')
    def test_acl_exists_recreate(self, f_manilaclient, f_context):

        share = _FakeShare(access_list=[mock.Mock(
            access_level='ro', access_to=ip, access_type='ip', id="access_id")
            for ip in _NAMENODE_IPS])
        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(return_value=share)))

        namenode_group, namenode_executors = _mock_node_group(
            _NAMENODE_IPS,
            [{
                'id': '12345678-1234-1234-1234-123456789012',
                'access_level': 'rw',
                'path': '/mnt/localpath'
            }])

        datanode_group, datanode_executors = _mock_node_group(
            _DATANODE_IPS, [])

        cluster = mock.Mock(
            node_groups=[namenode_group, datanode_group], shares=[])

        shares.mount_shares(cluster)

        namenode_denials = [mock.call('access_id')
                            for ip in _NAMENODE_IPS]
        share.deny.assert_has_calls(namenode_denials)

        namenode_permissions = [mock.call('ip', ip, 'rw')
                                for ip in _NAMENODE_IPS]
        share.allow.assert_has_calls(namenode_permissions,
                                     any_order=True)

        for executor in namenode_executors:
            executor.assert_has_calls(
                _setup_calls() +
                _expected_calls('/mnt/localpath', '192.168.122.1:/path', '-w'))
        for executor in datanode_executors:
            self.assertEqual(0, executor.call_count)

    def test_get_share_path(self):
        share_list = [
            {'id': 'the_share_id',
             'path': '/mnt/mymountpoint'},
            {'id': 'the_share_id',
             'path': '/mnt/othermountpoint'},
            {'id': '123456',
             'path': '/mnt/themountpoint'}
        ]
        url = 'manila://the_share_id/the_path'

        path = shares.get_share_path(url, share_list)
        self.assertEqual("/mnt/mymountpoint/the_path", path)

        share_list.pop(0)
        path = shares.get_share_path(url, share_list)
        self.assertEqual("/mnt/othermountpoint/the_path", path)

        share_list.pop(0)
        path = shares.get_share_path(url, share_list)
        self.assertIsNone(path)

    @mock.patch('sahara.utils.openstack.manila.client')
    def test_get_share_path_default(self, f_manilaclient):
        share_list = [
            {'id': 'i_have_no_mnt'}
        ]

        share = _FakeShare(share_list[0]['id'])
        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(return_value=share)))

        url = 'manila://i_have_no_mnt/the_path'
        path = shares.get_share_path(url, share_list)
        self.assertEqual("/mnt/i_have_no_mnt/the_path", path)
