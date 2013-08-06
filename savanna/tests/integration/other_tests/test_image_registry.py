# Copyright (c) 2013 Mirantis Inc.
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

import telnetlib

from savanna.tests.integration import base
import savanna.tests.integration.configs.parameters.common_parameters as param
import savanna.tests.integration.configs.parameters.vanilla_parameters as v_prm


def empty_object_id(expr):
    return '' if expr else v_prm.IMAGE_ID


@base.enable_test(param.ENABLE_IR_TESTS)
class ImageRegistryCrudTest(base.ITestCase):

    def _check_images_list_accessible(self):
        self.get_object(self.url_images, empty_object_id(True), 200)

    def _set_description_and_username(self, description, username):
        url = self.url_images + '/' + v_prm.IMAGE_ID
        body = dict(
            description=description,
            username=username
        )
        data = self.post_object(url, body, 202)
        return data

    def _send_rest_on_tag(self, url_part, tag_name):
        url = self.url_images + '/' + v_prm.IMAGE_ID + url_part
        tag = [tag_name]
        body = dict(tags=tag)
        data = self.post_object(url, body, 202)
        return data

    def _get_image_description(self):
        url = self.url_images + '/'
        data = self.get_object(url, empty_object_id(False), 200)
        return data

    def _set_and_compare_tags(self, tag):
        data = self._get_image_description()
        tag_data = data['image']['tags']
        if tag not in data['image']['tags']:
            data = self._send_rest_on_tag('/tag', tag)
            tag_data.append(tag)
        self.assertItemsEqual(data['image']['tags'], tag_data,
                              'Tags comparison has failed')
        return tag_data

    def _delete_tag_and_check(self, tag):
        data = self._get_image_description()
        untag_data = data['image']['tags']
        data = self._send_rest_on_tag('/untag', tag)
        untag_data.remove(tag)
        self.assertItemsEqual(data['image']['tags'], untag_data,
                              'Tags comparison has failed')

    def _get_image_by_tags(self, tag_name):
        url = self.url_images + '?tags=' + tag_name
        data = self.get_object(url, empty_object_id(True), 200)
        if v_prm.IMAGE_ID not in [img['id'] for img in data['images']]:
            self.fail('Image by tag \'%s\' not found' % tag_name)

    def _get_image_by_delete_tags(self, tag_name):
        url = self.url_images + '?tags=' + tag_name
        data = self.get_object(url, empty_object_id(True), 200)
        if v_prm.IMAGE_ID in [img['id'] for img in data['images']]:
            self.fail('Image tag \'%s\' is not deleted' % tag_name)

    def setUp(self):
        super(ImageRegistryCrudTest, self).setUp()
        telnetlib.Telnet(self.host, self.port)

    def test_image_registry(self):
        """This test checks image registry work
        """
        tag1_name = 'animal'
        tag2_name = 'dog'
        description = 'working image'

        self._check_images_list_accessible()

        old_image_username = self._get_image_description()['image']['username']

        try:
            data = self._set_description_and_username(
                description, v_prm.NODE_USERNAME)
            self.assertEqual(data['image']['description'], description)
            self.assertEqual(data['image']['username'], v_prm.NODE_USERNAME)

            self._set_and_compare_tags(tag1_name)
            tag_data = self._set_and_compare_tags(tag2_name)

            self._get_image_by_tags(tag1_name)
            self._get_image_by_tags(tag2_name)

            data = self._get_image_description()

            self.assertEqual(data['image']['status'], 'ACTIVE')
            self.assertEqual(data['image']['username'], v_prm.NODE_USERNAME)
            self.assertItemsEqual(data['image']['tags'], tag_data)
            self.assertEqual(data['image']['description'], description)
            self.assertEqual(data['image']['id'], v_prm.IMAGE_ID)

            self._delete_tag_and_check(tag1_name)
            self._delete_tag_and_check(tag2_name)

            self._get_image_by_delete_tags(tag1_name)
            self._get_image_by_delete_tags(tag2_name)

            self._check_images_list_accessible()

        except Exception as e:
            self._send_rest_on_tag('/untag', tag1_name)
            self._send_rest_on_tag('/untag', tag2_name)

            self.fail('Image registry test has failed: ' + str(e))

        finally:
            self._set_description_and_username(description, old_image_username)
