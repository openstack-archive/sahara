# Copyright (c) 2017 EasyStack Inc.
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

from sahara.service.api.v2 import images
from sahara.tests.unit import base


class TestImageApi(base.SaharaTestCase):
    def SetUp(self):
        super(TestImageApi, self).SetUp()

    @mock.patch('sahara.utils.openstack.images.SaharaImageManager')
    def test_get_image_tags(self, mock_manager):
        image = mock.Mock()
        manager = mock.Mock()
        manager.get.return_value = mock.Mock(tags=['foo', 'bar', 'baz'])
        mock_manager.return_value = manager
        self.assertEqual(['foo', 'bar', 'baz'], images.get_image_tags(image))

    @mock.patch('sahara.utils.openstack.images.SaharaImageManager')
    def test_set_image_tags(self, mock_manager):
        def _tag(image, to_add):
            return tags.append('qux')

        def _untag(image, to_remove):
            return tags.remove('bar')

        expected_tags = ['foo', 'baz', 'qux']
        tags = ['foo', 'bar', 'baz']
        image = mock.Mock()
        manager = mock.Mock()
        manager.get.return_value = mock.Mock(tags=tags)
        manager.tag.side_effect = _tag
        manager.untag.side_effect = _untag
        mock_manager.return_value = manager

        self.assertEqual(expected_tags,
                         images.set_image_tags(image, expected_tags).tags)

    @mock.patch('sahara.utils.openstack.images.SaharaImageManager')
    def test_remove_image_tags(self, mock_manager):
        def _untag(image, to_remove):
            for i in range(len(to_remove)):
                actual_tags.pop()
            return actual_tags

        actual_tags = ['foo', 'bar', 'baz']
        image = mock.Mock()
        manager = mock.Mock()
        manager.get.return_value = mock.Mock(tags=actual_tags)
        manager.untag.side_effect = _untag
        mock_manager.return_value = manager

        self.assertEqual([], images.remove_image_tags(image).tags)
