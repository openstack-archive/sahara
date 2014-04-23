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

import unittest2

from sahara.service import direct_engine as e


class TestDirectEngine(unittest2.TestCase):
    def setUp(self):
        self.engine = e.DirectEngine()
        super(TestDirectEngine, self).setUp()

    def test_get_inst_name(self):
        inst_name = "cluster-worker-001"
        self.assertEqual(
            self.engine._get_inst_name("cluster", "worker", 1), inst_name)
        self.assertEqual(
            self.engine._get_inst_name("CLUSTER", "WORKER", 1), inst_name)
