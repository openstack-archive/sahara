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

from sahara.service.validations import shares
from sahara.tests.unit.service.validation import utils as u


class TestShareValidations(u.ValidationTestCase):

    def setUp(self):
        super(TestShareValidations, self).setUp()
        self._create_object_fun = shares.check_shares
        self.scheme = shares.SHARE_SCHEMA

    @mock.patch('sahara.utils.openstack.manila.client')
    def test_shares(self, f_client):
        f_client.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(
                    return_value=mock.Mock(share_proto='NFS'))))

        self._assert_create_object_validation(data=[
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "path": "/path",
                "access_level": 'rw'
            }])

    @mock.patch('sahara.utils.openstack.manila.client')
    def test_shares_bad_type(self, f_client):
        f_client.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(
                    return_value=mock.Mock(share_proto='Mackerel'))))

        self._assert_create_object_validation(
            data=[
                {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "path": "/path",
                    "access_level": 'rw'
                }],
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Requested share id "
                       "12345678-1234-1234-1234-123456789012 is of type "
                       "Mackerel, which is not supported by Sahara."))

    @mock.patch('sahara.utils.openstack.manila.client')
    def test_shares_overlapping_paths(self, f_client):

        self._assert_create_object_validation(
            data=[
                {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "path": "/path",
                },
                {
                    "id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                    "path": "/path"
                }],
            bad_req_i=(1, 'INVALID_DATA',
                       "Multiple shares cannot be mounted to the same path."))

        self.assertEqual(0, f_client.call_count)

    @mock.patch('sahara.utils.openstack.manila.client')
    def test_shares_no_share_exists(self, f_client):
        f_client.return_value = mock.Mock(
            shares=mock.Mock(
                get=mock.Mock(
                    side_effect=manila_ex.NotFound)))

        self._assert_create_object_validation(
            data=[
                {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "path": "/path"
                }],
            bad_req_i=(
                1, 'INVALID_REFERENCE',
                "Requested share id 12345678-1234-1234-1234-123456789012 does "
                "not exist."))

    @mock.patch('sahara.utils.openstack.manila.client')
    def test_shares_bad_paths(self, f_client):

        self._assert_create_object_validation(
            data=[
                {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "path": "path"
                }],
            bad_req_i=(
                1, 'INVALID_DATA',
                'Paths must be absolute Linux paths starting with "/" '
                'and may not contain nulls.'))

        self._assert_create_object_validation(
            data=[
                {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "path": "\x00"
                }],
            bad_req_i=(
                1, 'INVALID_DATA',
                'Paths must be absolute Linux paths starting with "/" '
                'and may not contain nulls.'))

        self.assertEqual(0, f_client.call_count)

    @mock.patch('sahara.utils.openstack.manila.client')
    def test_shares_no_shares(self, f_client):
        self._assert_create_object_validation(data=[])
        self.assertEqual(0, f_client.call_count)
