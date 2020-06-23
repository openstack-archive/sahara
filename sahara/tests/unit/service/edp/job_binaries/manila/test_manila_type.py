# Copyright (c) 2017 OpenStack Foundation
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

from oslo_utils import uuidutils
import testtools

import sahara.exceptions as ex
from sahara.service.edp.job_binaries.manila import implementation
from sahara.tests.unit import base


class _FakeShare(object):
    def __init__(self, id, share_proto='NFS'):
        self.id = id
        self.share_proto = share_proto


class TestManilaType(base.SaharaTestCase):

    def setUp(self):
        super(TestManilaType, self).setUp()
        self.manila_type = implementation.ManilaType()

    def test_validate_job_location_format(self):

        invalid_url_1 = 'manila://abc'
        invalid_url_2 = 'manila://' + uuidutils.generate_uuid()
        valid_url = 'manila://' + uuidutils.generate_uuid() + '/path'

        self.assertFalse(self.manila_type.validate_job_location_format(''))
        self.assertFalse(self.manila_type.
                         validate_job_location_format(invalid_url_1))
        self.assertFalse(self.manila_type.
                         validate_job_location_format(invalid_url_2))

        self.assertTrue(self.manila_type.
                        validate_job_location_format(valid_url))

    @mock.patch('sahara.service.edp.utils.shares.default_mount')
    @mock.patch('sahara.utils.openstack.manila.client')
    def test_copy_binary_to_cluster(self, f_manilaclient, default_mount):
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

        info = self.manila_type.copy_binary_to_cluster(job_binary,
                                                       remote=remote)

        self.assertCountEqual('/mnt/mymountpoint/the_path', info)

        job_binary.url = 'manila://123456/the_path'
        info = self.manila_type.copy_binary_to_cluster(job_binary,
                                                       remote=remote)
        self.assertCountEqual('/mnt/themountpoint/the_path', info)

        # missing id
        default_mount.return_value = '/mnt/missing_id'

        job_binary.url = 'manila://missing_id/the_path'
        info = self.manila_type.copy_binary_to_cluster(job_binary,
                                                       remote=remote)

        self.assertCountEqual('/mnt/missing_id/the_path', info)

    @mock.patch('sahara.utils.openstack.manila.client')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.service.edp.utils.shares.mount_shares')
    def test_prepare_cluster(self, mount_shares, cluster_update,
                             f_manilaclient):

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

        remote = mock.Mock()
        remote.instance.node_group.cluster.shares = cluster_shares
        remote.instance.node_group.shares = ng_shares

        # This should return a default path, and should cause
        # a mount at the default location
        share = _FakeShare("missing_id")
        f_manilaclient.return_value = mock.Mock(shares=mock.Mock(
            get=mock.Mock(return_value=share)))

        job_binary.url = 'manila://missing_id/the_path'

        self.manila_type.prepare_cluster(job_binary, remote=remote)
        self.assertEqual(1, mount_shares.call_count)
        self.assertEqual(1, cluster_update.call_count)

    def test_get_raw_data(self):
        with testtools.ExpectedException(ex.NotImplementedException):
            self.manila_type.get_raw_data({})

    def test_data_validation(self):
        data = {
            "name": "test",
            "url": "man://%s" % uuidutils.generate_uuid(),
            "type": "manila",
            "description": ("incorrect url schema for")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

        data = {
            "name": "test",
            "url": "",
            "type": "manila",
            "description": ("empty url")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

        data = {
            "name": "test",
            "url": "manila://bob",
            "type": "manila",
            "description": ("netloc is not a uuid")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

        data = {
            "name": "test",
            "url": "manila://%s" % uuidutils.generate_uuid(),
            "type": "manila",
            "description": ("netloc is not a uuid")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

        data = {
            "name": "test",
            "url": "manila://%s/foo" % uuidutils.generate_uuid(),
            "type": "manila",
            "description": ("correct url")
        }
        self.manila_type.validate(data)
