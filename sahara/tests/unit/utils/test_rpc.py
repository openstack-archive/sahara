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

import mock

from sahara import main
from sahara.tests.unit import base
from sahara.utils import rpc as messaging

_ALIASES = {
    'sahara.openstack.common.rpc.impl_kombu': 'rabbit',
    'sahara.openstack.common.rpc.impl_qpid': 'qpid',
    'sahara.openstack.common.rpc.impl_zmq': 'zmq',
}


class TestMessagingSetup(base.SaharaTestCase):
    @mock.patch('oslo_messaging.set_transport_defaults')
    @mock.patch('oslo_messaging.get_transport')
    @mock.patch('oslo_messaging.Notifier')
    def test_set_defaults(self, notifier_init,
                          get_transport, set_transport_def):
        self.override_config('enable', True,
                             group='oslo_messaging_notifications')

        messaging.setup()
        self.assertIsNotNone(messaging.TRANSPORT)
        self.assertIsNotNone(messaging.NOTIFIER)

        expected = [
            mock.call('sahara')
        ]
        self.assertEqual(expected, set_transport_def.call_args_list)
        self.assertEqual(
            [mock.call(main.CONF, aliases=_ALIASES)],
            get_transport.call_args_list)
        self.assertEqual(1, notifier_init.call_count)

        if messaging.TRANSPORT:
            messaging.TRANSPORT.cleanup()
            messaging.TRANSPORT = messaging.NOTIFIER = None
