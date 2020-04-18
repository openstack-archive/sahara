# Copyright (c) 2016 SUSE LINUX Products GmbH
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

import testtools
from unittest import mock

from sahara import context
from sahara import main


def mock_validate_config():
    return mock.patch(
        'sahara.service.castellan.config.validate_config')


class SomeException(Exception):
    pass


class ValidateCastellanTest(testtools.TestCase):

    def test_castellan_validate_config_called(self):
        with mock_validate_config() as validate_config:
            main.validate_castellan_config()

        validate_config.assert_called_once_with()

    def test_context_present_when_calling_validate_config(self):

        def check_context():
            self.assertTrue(context.has_ctx())

        with mock_validate_config() as validate_config:
            validate_config.side_effect = check_context
            main.validate_castellan_config()

    def test_context_cleared(self):
        with mock_validate_config():
            main.validate_castellan_config()

        self.assertFalse(context.has_ctx())

    def test_context_cleared_in_case_of_exception(self):
        with mock_validate_config() as validate_config:
            validate_config.side_effect = SomeException
            self.assertRaises(SomeException, main.validate_castellan_config)

        self.assertFalse(context.has_ctx())
