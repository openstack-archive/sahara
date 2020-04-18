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
from sahara.service.edp.data_sources.manila.implementation import ManilaType
from sahara.tests.unit import base


class _FakeShare(object):
    def __init__(self, id, share_proto='NFS'):
        self.id = id
        self.share_proto = share_proto


class TestManilaType(base.SaharaTestCase):
    def setUp(self):
        super(TestManilaType, self).setUp()
        self.manila_type = ManilaType()

    @mock.patch('sahara.utils.openstack.manila.client')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.service.edp.utils.shares.mount_shares')
    def test_prepare_cluster(self, mount_shares, cluster_update,
                             f_manilaclient):

        cluster_shares = [
            {'id': 'the_share_id',
             'path': '/mnt/mymountpoint'}
        ]

        cluster = mock.Mock()
        cluster.shares = cluster_shares

        # This should return a default path, and should cause
        # a mount at the default location
        share = _FakeShare("missing_id")
        f_manilaclient.return_value = mock.Mock(shares=mock.Mock(
            get=mock.Mock(return_value=share)))

        url = 'manila://missing_id/the_path'
        self.manila_type._prepare_cluster(url, cluster)

        self.assertEqual(1, mount_shares.call_count)
        self.assertEqual(1, cluster_update.call_count)

    @mock.patch('sahara.service.edp.utils.shares.get_share_path')
    @mock.patch('sahara.utils.openstack.manila.client')
    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.service.edp.utils.shares.mount_shares')
    def test_get_runtime_url(self, mount_shares, cluster_update,
                             f_manilaclient, get_share_path):

        # first it finds the path, then it doesn't so it has to mount it
        # and only then it finds it
        get_share_path.side_effect = ['/mnt/mymountpoint/the_path', None,
                                      '/mnt/missing_id/the_path']

        cluster = mock.Mock()
        cluster.shares = []
        url = 'manila://the_share_id/the_path'

        res = self.manila_type.get_runtime_url(url, cluster)
        self.assertEqual('file:///mnt/mymountpoint/the_path', res)
        self.assertEqual(0, mount_shares.call_count)
        self.assertEqual(0, cluster_update.call_count)

        # This should return a default path, and should cause
        # a mount at the default location
        share = _FakeShare("missing_id")
        f_manilaclient.return_value = mock.Mock(shares=mock.Mock(
            get=mock.Mock(return_value=share)))

        url = 'manila://missing_id/the_path'
        res = self.manila_type.get_runtime_url(url, cluster)
        self.assertEqual('file:///mnt/missing_id/the_path', res)
        self.assertEqual(1, mount_shares.call_count)
        self.assertEqual(1, cluster_update.call_count)

    def test_manila_type_validation_wrong_schema(self):
        data = {
            "name": "test_data_data_source",
            "url": "man://%s" % uuidutils.generate_uuid(),
            "type": "manila",
            "description": ("incorrect url schema for")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

    def test_manila_type_validation_empty_url(self):
        data = {
            "name": "test_data_data_source",
            "url": "",
            "type": "manila",
            "description": ("empty url")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

    def test_manila_type_validation_no_uuid(self):
        data = {
            "name": "test_data_data_source",
            "url": "manila://bob",
            "type": "manila",
            "description": ("netloc is not a uuid")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

    def test_manila_type_validation_no_path(self):
        data = {
            "name": "test_data_data_source",
            "url": "manila://%s" % uuidutils.generate_uuid(),
            "type": "manila",
            "description": ("netloc is not a uuid")
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.manila_type.validate(data)

    def test_manila_type_validation_correct(self):
        data = {
            "name": "test_data_data_source",
            "url": "manila://%s/foo" % uuidutils.generate_uuid(),
            "type": "manila",
            "description": ("correct url")
        }
        self.manila_type.validate(data)
