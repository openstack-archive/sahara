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
from sahara.utils.openstack import glance as glance_client


class FakeImage(object):
    def __init__(self, name, tags, username):
        self.name = name
        self.tags = tags
        self.username = username


class TestImages(base.SaharaTestCase):
    def setUp(self):
        super(TestImages, self).setUp()
        self.override_config('auth_uri', 'https://127.0.0.1:8080/v3/',
                             'keystone_authtoken')

    @mock.patch('sahara.utils.openstack.base.url_for', return_value='')
    def test_list_registered_images(self, url_for_mock):
        some_images = [
            FakeImage('foo', ['bar', 'baz'], 'test'),
            FakeImage('baz', [], 'test'),
            FakeImage('spam', [], "")]

        with mock.patch('glanceclient.v2.images.Controller.list',
                        return_value=some_images):
            glance = glance_client.client()

            images = glance.images.list_registered()
            self.assertEqual(2, len(images))

            images = glance.images.list_registered(name='foo')
            self.assertEqual(1, len(images))
            self.assertEqual('foo', images[0].name)
            self.assertEqual('test', images[0].username)

            images = glance.images.list_registered(name='eggs')
            self.assertEqual(0, len(images))

            images = glance.images.list_registered(tags=['bar'])
            self.assertEqual(1, len(images))
            self.assertEqual('foo', images[0].name)

            images = glance.images.list_registered(tags=['bar', 'eggs'])
            self.assertEqual(0, len(images))

    @mock.patch('sahara.utils.openstack.images.SaharaImageManager.set_meta')
    def test_set_description(self, set_meta):
        with mock.patch('sahara.utils.openstack.base.url_for'):
            glance = glance_client.client()
            glance.images.set_description('id', 'ubuntu')
            self.assertEqual(
                ('id', {'_sahara_username': 'ubuntu'}), set_meta.call_args[0])

            glance.images.set_description('id', 'ubuntu', 'descr')
            self.assertEqual(
                ('id', {'_sahara_description': 'descr',
                        '_sahara_username': 'ubuntu'}),
                set_meta.call_args[0])

    @mock.patch('sahara.utils.openstack.images.SaharaImageManager.get')
    @mock.patch('sahara.utils.openstack.images.SaharaImageManager.delete_meta')
    def test_unset_description(self, delete_meta, get_image):
            glance = glance_client.client()
            image = mock.MagicMock()
            image.tags = ['fake', 'fake_2.0']
            image.username = 'ubuntu'
            image.description = 'some description'
            get_image.return_value = image
            glance.images.unset_description('id')
            self.assertEqual(
                ('id', ['_sahara_tag_fake', '_sahara_tag_fake_2.0',
                        '_sahara_description', '_sahara_username']),
                delete_meta.call_args[0])
