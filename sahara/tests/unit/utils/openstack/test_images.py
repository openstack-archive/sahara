# Copyright (c) 2015 Mirantis Inc.
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

import mock

from sahara.tests.unit import base
from sahara.utils.openstack import nova as nova_client


class FakeImage(object):
    def __init__(self, name, tags, username):
        self.name = name
        self.tags = tags
        self.username = username


class TestImages(base.SaharaTestCase):
    @mock.patch('sahara.utils.openstack.base.url_for', return_value='')
    def test_list_registered_images(self, url_for_mock):
        some_images = [
            FakeImage('foo', ['bar', 'baz'], 'test'),
            FakeImage('baz', [], 'test'),
            FakeImage('spam', [], "")]

        with mock.patch('novaclient.v2.images.ImageManager.list',
                        return_value=some_images):
            nova = nova_client.client()

            images = nova.images.list_registered()
            self.assertEqual(2, len(images))

            images = nova.images.list_registered(name='foo')
            self.assertEqual(1, len(images))
            self.assertEqual('foo', images[0].name)
            self.assertEqual('test', images[0].username)

            images = nova.images.list_registered(name='eggs')
            self.assertEqual(0, len(images))

            images = nova.images.list_registered(tags=['bar'])
            self.assertEqual(1, len(images))
            self.assertEqual('foo', images[0].name)

            images = nova.images.list_registered(tags=['bar', 'eggs'])
            self.assertEqual(0, len(images))
