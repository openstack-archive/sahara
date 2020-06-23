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

from unittest import mock

import sahara.service.edp.binary_retrievers.manila_share as ms
from sahara.tests.unit import base


class _FakeShare(object):
    def __init__(self, id, share_proto='NFS'):
        self.id = id
        self.share_proto = share_proto


class TestManilaShare(base.SaharaTestCase):
    def setUp(self):
        super(TestManilaShare, self).setUp()

    @mock.patch('sahara.utils.openstack.manila.client')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.service.edp.utils.shares.mount_shares')
    def test_get_file_info(self, mount_shares, cluster_update, f_manilaclient):
        cluster_shares = [
            {'id': 'the_share_id',
             'path': '/mnt/mymountpoint'}
        ]

        ng_shares = [
            {'id': 'the_share_id',
             'path': '/mnt/othermountpoint'},
            {'id': '123456',
             'path': '/mnt/themountpoint'}
        ]

        job_binary = mock.Mock()
        job_binary.url = 'manila://the_share_id/the_path'

        remote = mock.Mock()
        remote.instance.node_group.cluster.shares = cluster_shares
        remote.instance.node_group.shares = ng_shares

        info = ms.get_file_info(job_binary, remote)
        self.assertCountEqual({'path': '/mnt/mymountpoint/the_path',
                               'type': 'path'}, info)
        self.assertEqual(0, mount_shares.call_count)
        self.assertEqual(0, cluster_update.call_count)

        job_binary.url = 'manila://123456/the_path'
        info = ms.get_file_info(job_binary, remote)
        self.assertCountEqual({'path': '/mnt/themountpoint/the_path',
                               'type': 'path'}, info)
        self.assertEqual(0, mount_shares.call_count)
        self.assertEqual(0, cluster_update.call_count)

        # This should return a default path, and should cause
        # a mount at the default location
        share = _FakeShare("missing_id")
        f_manilaclient.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(return_value=share)))

        job_binary.url = 'manila://missing_id/the_path'
        info = ms.get_file_info(job_binary, remote)
        self.assertCountEqual({'path': '/mnt/missing_id/the_path',
                               'type': 'path'}, info)
        self.assertEqual(1, mount_shares.call_count)
        self.assertEqual(1, cluster_update.call_count)
