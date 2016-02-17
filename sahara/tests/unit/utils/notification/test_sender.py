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

from sahara import context
from sahara.tests.unit import base
from sahara.utils.notification import sender
from sahara.utils import rpc as messaging


class NotificationTest(base.SaharaTestCase):

    def setUp(self):
        super(NotificationTest, self).setUp()

    def _make_sample(self):
        ctx = context.ctx()

        self.ctx = ctx
        self.cluster_id = 'someId'
        self.cluster_name = 'someName'
        self.cluster_status = 'someStatus'

        sender.status_notify(self.cluster_id, self.cluster_name,
                             self.cluster_status, "update")

        self.create_mock('update')

    def create_mock(self, action):

        self.expected = mock.call(self.ctx,
                                  'sahara.cluster.%s' % action,
                                  {'cluster_id': self.cluster_id,
                                   'cluster_name': self.cluster_name,
                                   'cluster_status': self.cluster_status,
                                   'project_id': self.ctx.tenant_id,
                                   'user_id': self.ctx.user_id})

    @mock.patch('oslo_messaging.notify.notifier.Notifier.info')
    def test_update_cluster(self, mock_notify):
        self.override_config("enable", True,
                             group='oslo_messaging_notifications')
        messaging.setup()

        self._make_sample()
        self.assertEqual([self.expected],
                         mock_notify.call_args_list)

        if messaging.TRANSPORT:
            messaging.TRANSPORT.cleanup()
            messaging.TRANSPORT = messaging.NOTIFIER = None
