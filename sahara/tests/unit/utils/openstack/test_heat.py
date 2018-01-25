# Copyright (c) 2017 Massachusetts Open Cloud
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
import testtools

from sahara.utils.openstack import heat as heat_u


class HeatClientTest(testtools.TestCase):
    @mock.patch('heatclient.client.Client')
    @mock.patch('sahara.utils.openstack.base.url_for')
    @mock.patch('sahara.service.sessions.cache')
    @mock.patch('sahara.context.ctx')
    def test_abandon(self, ctx, cache, url_for, heat):
        class _FakeHeatStacks(object):
            def delete(self, stack):
                call_list.append("delete")

            def abandon(self, stack):
                call_list.append("abandon")

        heat.return_value.stacks = _FakeHeatStacks()

        call_list = []
        heat_u.abandon_stack(mock.Mock())
        self.assertEqual(call_list, ["delete", "abandon"])
