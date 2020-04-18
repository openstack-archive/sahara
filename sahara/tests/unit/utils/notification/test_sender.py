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

from sahara import context
from sahara.tests.unit import base
from sahara.utils.notification import sender


class NotificationTest(base.SaharaTestCase):
    @mock.patch('sahara.utils.rpc.get_notifier')
    def test_update_cluster(self, mock_notify):
        class FakeNotifier(object):
            def info(self, *args):
                self.call = args

        notifier = FakeNotifier()
        mock_notify.return_value = notifier
        ctx = context.ctx()
        sender.status_notify('someId', 'someName', 'someStatus', "update")
        self.expected_args = (ctx,
                              'sahara.cluster.%s' % 'update',
                              {'cluster_id': 'someId',
                               'cluster_name': 'someName',
                               'cluster_status': 'someStatus',
                               'project_id': ctx.tenant_id,
                               'user_id': ctx.user_id})

        self.assertEqual(self.expected_args,
                         notifier.call)
