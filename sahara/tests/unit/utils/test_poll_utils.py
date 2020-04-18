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

from unittest import mock

import six
import testtools

from sahara import context
from sahara.tests.unit import base
from sahara.utils import poll_utils


class FakeCluster(object):
    def __init__(self, cluster_configs):
        self.cluster_configs = cluster_configs


class FakeOption(object):
    def __init__(self, default_value, section, name):
        self.default_value = default_value
        self.name = name
        self.applicable_target = section


class TestPollUtils(base.SaharaTestCase):
    def setUp(self):
        super(TestPollUtils, self).setUp()
        context.sleep = mock.Mock()

    @mock.patch('sahara.utils.poll_utils.LOG.debug')
    def test_poll_success(self, logger):
        poll_utils.poll(**{'get_status': lambda: True,
                           'kwargs': {}, 'timeout': 5, 'sleep': 3})
        expected_call = mock.call(
            'Operation was executed successfully in timeout 5')
        self.assertEqual(1, logger.call_count)
        self.assertEqual([expected_call], logger.call_args_list)

    @mock.patch('sahara.utils.poll_utils._get_consumed')
    def test_poll_failed_first_scenario(self, get_consumed):
        get_consumed.return_value = 0
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

    @mock.patch('sahara.utils.poll_utils._get_consumed')
    def test_poll_failed_second_scenario(self, get_consumed):
        get_consumed.return_value = 0
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

    @mock.patch('sahara.utils.poll_utils.LOG.debug')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    def test_plugin_poll_first_scenario(self, cluster_exists, logger):
        cluster_exists.return_value = True
        fake_get_status = mock.Mock()
        fake_get_status.side_effect = [False, False, True]
        fake_kwargs = {'kwargs': {'cat': 'tom', 'bond': 'james bond'}}
        poll_utils.plugin_option_poll(
            FakeCluster({}), fake_get_status, FakeOption(5, 'target', 'name'),
            'fake_operation', 5, **fake_kwargs)
        expected_call = mock.call('Operation with name fake_operation was '
                                  'executed successfully in timeout 5')
        self.assertEqual([expected_call], logger.call_args_list)

    @mock.patch('sahara.utils.poll_utils.LOG.debug')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    def test_plugin_poll_second_scenario(self, cluster_exists, logger):
        cluster_exists.return_value = False
        fake_get_status = mock.Mock()
        fake_get_status.side_effect = [False, False, True]
        fake_kwargs = {'kwargs': {'cat': 'tom', 'bond': 'james bond'}}
        poll_utils.plugin_option_poll(
            FakeCluster({'target': {'name': 7}}), fake_get_status,
            FakeOption(5, 'target', 'name'),
            'fake_operation', 5, **fake_kwargs)

        expected_call = mock.call('Operation with name fake_operation was '
                                  'executed successfully in timeout 7')
        self.assertEqual([expected_call], logger.call_args_list)

    def test_poll_exception_strategy_first_scenario(self):
        fake_get_status = mock.Mock()
        fake_get_status.side_effect = [False, ValueError()]

        with testtools.ExpectedException(ValueError):
            poll_utils.poll(fake_get_status)

    def test_poll_exception_strategy_second_scenario(self):
        fake_get_status = mock.Mock()
        fake_get_status.side_effect = [False, ValueError()]
        poll_utils.poll(fake_get_status, exception_strategy='mark_as_true')
        self.assertEqual(2, fake_get_status.call_count)

    def test_poll_exception_strategy_third_scenario(self):
        fake_get_status = mock.Mock()
        fake_get_status.side_effect = [False, ValueError(), True]
        poll_utils.poll(fake_get_status, exception_strategy='mark_as_false')
        self.assertEqual(3, fake_get_status.call_count)
