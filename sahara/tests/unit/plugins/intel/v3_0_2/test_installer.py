# Copyright (c) 2014 Intel Corporation
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

from sahara.plugins.intel.v3_0_2 import installer
from sahara.tests.unit import base


class InstallerTest(base.SaharaTestCase):
    def test_is_hadoop_service_stopped(self):
        instance = mock.Mock()
        instance.remote.return_value.execute_command.return_value = (
            1, "Hadoop datanode is not running    [FAILURE]")
        self.assertTrue(
            installer._is_hadoop_service_stopped(instance, 'datanode'))

        instance = mock.Mock()
        instance.remote.return_value.execute_command.return_value = (
            1, "Hadoop datanode is dead and pid file exists    [FAILURE]")
        self.assertTrue(
            installer._is_hadoop_service_stopped(instance, 'datanode'))

        instance = mock.Mock()
        instance.remote.return_value.execute_command.return_value = (
            0, "Hadoop datanode is running    [SUCCESS]")
        self.assertFalse(
            installer._is_hadoop_service_stopped(instance, 'datanode'))
