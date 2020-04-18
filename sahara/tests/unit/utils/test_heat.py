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

import testtools
from unittest import mock

from sahara import exceptions as ex
from sahara.utils.openstack import heat as h


def stack(status, upd_time=None):
    status_reason = status
    status = status[status.index('_') + 1:]
    return mock.Mock(status=status, updated_time=upd_time,
                     stack_status_reason=status_reason)


class TestClusterStack(testtools.TestCase):
    @mock.patch('sahara.utils.openstack.heat.get_stack')
    @mock.patch("sahara.context.sleep", return_value=None)
    def test_wait_completion(self, sleep, client):
        cl = mock.Mock(stack_name='cluster')
        client.side_effect = [stack(
            'CREATE_IN_PROGRESS'), stack('CREATE_COMPLETE')]
        h.wait_stack_completion(cl)
        self.assertEqual(2, client.call_count)

        client.side_effect = [
            stack('UPDATE_IN_PROGRESS'), stack('UPDATE_COMPLETE')]
        h.wait_stack_completion(cl)
        self.assertEqual(4, client.call_count)

        client.side_effect = [
            stack('DELETE_IN_PROGRESS'), stack('DELETE_COMPLETE')]
        h.wait_stack_completion(cl)
        self.assertEqual(6, client.call_count)

        client.side_effect = [
            stack('CREATE_COMPLETE'), stack('CREATE_COMPLETE'),
            stack('UPDATE_IN_PROGRESS'), stack('UPDATE_COMPLETE', 1)]

        h.wait_stack_completion(cl, is_update=True)
        self.assertEqual(10, client.call_count)

        client.side_effect = [stack('UPDATE_COMPLETE'), stack(
            'UPDATE_IN_PROGRESS'), stack('UPDATE_COMPLETE', 1)]
        h.wait_stack_completion(cl, is_update=True)
        self.assertEqual(13, client.call_count)

        client.side_effect = [
            stack('CREATE_IN_PROGRESS'), stack('CREATE_FAILED')]
        with testtools.ExpectedException(
                ex.HeatStackException,
                value_re=("Heat stack failed with status "
                          "CREATE_FAILED\nError ID: .*")):
            h.wait_stack_completion(cl)
