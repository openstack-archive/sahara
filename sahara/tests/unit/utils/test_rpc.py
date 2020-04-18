# Copyright (c) 2014 Mirantis Inc.
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

from sahara import main
from sahara.tests.unit import base
from sahara.utils import rpc as messaging


class TestMessagingSetup(base.SaharaTestCase):
    def setUp(self):
        super(TestMessagingSetup, self).setUp()
        self.patchers = []
        notifier_init_patch = mock.patch('oslo_messaging.Notifier')
        self.notifier_init = notifier_init_patch.start()
        self.patchers.append(notifier_init_patch)

        get_notif_transp_patch = mock.patch(
            'oslo_messaging.get_notification_transport')
        self.get_notify_transport = get_notif_transp_patch.start()
        self.patchers.append(get_notif_transp_patch)

        get_transport_patch = mock.patch('oslo_messaging.get_rpc_transport')
        self.get_transport = get_transport_patch.start()
        self.patchers.append(get_transport_patch)

        set_def_patch = mock.patch('oslo_messaging.set_transport_defaults')
        self.set_transport_def = set_def_patch.start()
        self.patchers.append(set_def_patch)

    def tearDown(self):
        messaging.NOTIFICATION_TRANSPORT = None
        messaging.MESSAGING_TRANSPORT = None
        messaging.NOTIFIER = None
        for patch in reversed(self.patchers):
            patch.stop()
        super(TestMessagingSetup, self).tearDown()

    def test_set_defaults(self):
        messaging.setup('distributed')

        self.assertIsNotNone(messaging.MESSAGING_TRANSPORT)
        self.assertIsNotNone(messaging.NOTIFICATION_TRANSPORT)
        self.assertIsNotNone(messaging.NOTIFIER)

        expected = [
            mock.call('sahara')
        ]
        self.assertEqual(expected, self.set_transport_def.call_args_list)
        self.assertEqual(
            [mock.call(main.CONF)],
            self.get_transport.call_args_list)
        self.assertEqual(
            [mock.call(main.CONF)],
            self.get_notify_transport.call_args_list)
        self.assertEqual(1, self.notifier_init.call_count)

    def test_fallback(self):
        self.get_notify_transport.side_effect = ValueError()
        messaging.setup('distributed')

        self.assertIsNotNone(messaging.MESSAGING_TRANSPORT)
        self.assertIsNotNone(messaging.NOTIFICATION_TRANSPORT)
        self.assertEqual(
            messaging.MESSAGING_TRANSPORT, messaging.NOTIFICATION_TRANSPORT)
        self.assertIsNotNone(messaging.NOTIFIER)

        expected = [
            mock.call('sahara')
        ]
        self.assertEqual(expected, self.set_transport_def.call_args_list)
        self.assertEqual(
            [mock.call(main.CONF)],
            self.get_transport.call_args_list)
        self.assertEqual(
            [mock.call(main.CONF)],
            self.get_notify_transport.call_args_list)
        self.assertEqual(1, self.notifier_init.call_count)

    def test_only_notifications(self):
        messaging.setup('all-in-one')
        self.assertEqual(0, self.get_transport.call_count)
        self.assertEqual(1, self.get_notify_transport.call_count)
