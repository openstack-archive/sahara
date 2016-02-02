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

from sahara.service.validations import images as im
from sahara.tests.unit.service.validation import utils as u


class TestTagsAddingValidation(u.ValidationTestCase):
    def setUp(self):
        super(TestTagsAddingValidation, self).setUp()
        self._create_object_fun = im.check_tags
        self.scheme = im.image_tags_schema

    def test_add_tags_validation(self):
        right_tags = ['1', 'a', 'a_1', 'a.2', 'a.A', 'a-A']
        wrong_tags = ['a.', '_a', 'a..a']
        wrong_symbols = "!@#$%^&*,"

        data = {
            'tags': []
        }
        for tag in right_tags:
            data["tags"] = [tag]
            self._assert_create_object_validation(
                data=data)
        for tag in wrong_tags:
            data["tags"] = [tag]
            self._assert_create_object_validation(
                data=data,
                bad_req_i=(1, 'VALIDATION_ERROR',
                           u"tags[0]: '%s' is not a 'valid_tag'" % tag))
        for symb in wrong_symbols:
            tag = "a%sa" % symb
            data['tags'] = [tag]
            self._assert_create_object_validation(
                data=data,
                bad_req_i=(1, 'VALIDATION_ERROR',
                           u"tags[0]: '%s' is not a 'valid_tag'" % tag))
