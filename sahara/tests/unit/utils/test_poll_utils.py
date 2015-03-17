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
import six

from sahara.tests.unit import base
from sahara.utils import poll_utils


class TestPollUtils(base.SaharaTestCase):
    @mock.patch('sahara.utils.poll_utils.LOG.debug')
    def test_poll_success(self, logger):
        poll_utils.poll(**{'get_status': lambda: True,
                           'kwargs': {}, 'timeout': 5, 'sleep': 3})
        expected_call = mock.call(
            'Operation was executed successfully in timeout 5')
        self.assertEqual(1, logger.call_count)
        self.assertEqual([expected_call], logger.call_args_list)

    @mock.patch('sahara.context.sleep', return_value=None)
    @mock.patch('sahara.utils.poll_utils._get_consumed', return_value=0)
    def test_poll_failed_first_scenario(self, p_1, p_2):
        message = ""
        try:
            poll_utils.poll(
                **{'get_status': lambda: False, 'kwargs': {},
                   'timeout': 0, 'sleep': 3})
        except Exception as e:
            message = six.text_type(e)

        if message.find('Error ID') != -1:
            message = message.split("\n")[0]
        expected_message = "'Operation' timed out after 0 second(s)"

        self.assertEqual(expected_message, message)

    @mock.patch('sahara.context.sleep', return_value=None)
    @mock.patch('sahara.utils.poll_utils._get_consumed', return_value=0)
    def test_poll_failed_second_scenario(self, p_1, p_2):
        message = ""
        try:
            poll_utils.poll(
                **{'get_status': lambda: False, 'kwargs': {},
                   'timeout': 0, 'sleep': 3, 'timeout_name': "some timeout"})
        except Exception as e:
            message = six.text_type(e)

        if message.find('Error ID') != -1:
            message = message.split("\n")[0]
        expected_message = ("'Operation' timed out after 0 second(s) and "
                            "following timeout was violated: some timeout")

        self.assertEqual(expected_message, message)
