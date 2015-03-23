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

import mock
import testtools

from sahara.plugins.vanilla.v1_2_1 import run_scripts


class RunScriptsTest(testtools.TestCase):

    def test_check_datanodes_count_positive(self):
        remote = mock.Mock()
        remote.execute_command.return_value = (0, "1")
        self.assertTrue(run_scripts.check_datanodes_count(remote, 1))

    def test_check_datanodes_count_negative(self):
        remote = mock.Mock()
        remote.execute_command.return_value = (0, "1")
        self.assertFalse(run_scripts.check_datanodes_count(remote, 2))

    def test_check_datanodes_count_nonzero_exitcode(self):
        remote = mock.Mock()
        remote.execute_command.return_value = (1, "1")
        self.assertFalse(run_scripts.check_datanodes_count(remote, 1))

    def test_check_datanodes_count_expects_zero(self):
        remote = mock.Mock()
        self.assertTrue(run_scripts.check_datanodes_count(remote, 0))
        self.assertEqual(0, remote.execute_command.call_count)
