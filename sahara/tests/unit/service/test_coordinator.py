# Copyright (c) 2016 Mirantis Inc.
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

from sahara.service import coordinator
from sahara.tests.unit import base


class TestCoordinator(base.SaharaTestCase):
    def test_coord_without_backend(self):
        coord = coordinator.Coordinator('')
        self.assertIsNone(coord.coordinator)

    @mock.patch('tooz.coordination.get_coordinator')
    def test_coord_with_backend(self, get_coord):
        MockCoord = mock.Mock()
        MockCoord.start.return_value = mock.Mock()
        get_coord.return_value = MockCoord

        coord = coordinator.Coordinator('kazoo://1.2.3.4:2181')
        self.assertEqual(MockCoord, coord.coordinator)
        MockCoord.start.assert_called_once_with()


class TestHashRing(base.SaharaTestCase):
    def setUp(self):
        super(TestHashRing, self).setUp()
        self.override_config('hash_ring_replicas_count', 1)

    @mock.patch('tooz.coordination.get_coordinator', return_value=mock.Mock())
    def _init_hr(self, get_coord):
        self.hr = coordinator.HashRing('kazoo://1.2.3.4:2181', 'group')
        self.hr.get_members = mock.Mock(return_value=['id1', 'id2', 'id3'])
        self.hr.member_id = 'id2'
        self.hr._hash = mock.Mock(side_effect=[1, 10, 20, 5, 13, 25])

    def test_get_subset_without_backend(self):
        hr = coordinator.HashRing('', 'group')
        objects = [mock.Mock(id=1), mock.Mock(id=2)]
        # all objects will be managed by this engine if coordinator backend
        # is not provided
        self.assertEqual(objects, hr.get_subset(objects))

    def test_build_ring(self):
        # check hash ring with one replica
        self._init_hr()
        hr, keys = self.hr._build_ring()
        self.assertEqual({1: 'id1', 10: 'id2', 20: 'id3'}, hr)
        self.assertEqual([1, 10, 20], keys)

        # check hash ring with two replicas
        self.override_config('hash_ring_replicas_count', 2)
        self._init_hr()
        hr, keys = self.hr._build_ring()
        self.assertEqual(
            {1: 'id1', 5: 'id2', 10: 'id1', 13: 'id3', 20: 'id2', 25: 'id3'},
            hr)
        self.assertEqual([1, 5, 10, 13, 20, 25], keys)

    def test_check_object(self):
        self._init_hr()
        ring, keys = self.hr._build_ring()

        # this object will be managed by this engine
        self.assertTrue(
            self.hr._check_object(mock.Mock(id='123'), ring, keys))

        # this object will not be managed by this engine
        self.assertFalse(
            self.hr._check_object(mock.Mock(id='321'), ring, keys))

        # this object will not be managed by this engine
        self.assertFalse(
            self.hr._check_object(mock.Mock(id='213'), ring, keys))

    def test_get_subset_with_backend(self):
        self._init_hr()
        objects = [mock.Mock(id=123), mock.Mock(id=321), mock.Mock(id=213)]

        # only first object will be managed by this engine
        self.assertEqual([objects[0]], self.hr.get_subset(objects))
