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

from sahara.utils import general


class UtilsGeneralTest(testtools.TestCase):
    def test_find_dict(self):
        iterable = [
            {
                "a": 1
            },
            {
                "a": 1,
                "b": 2,
                "c": 3
            },
            {
                "a": 2
            },
            {
                "c": 3
            }
        ]

        self.assertEqual({"a": 1, "b": 2, "c": 3},
                         general.find_dict(iterable, a=1, b=2))

    def test_generate_instance_name(self):
        inst_name = "cluster-worker-001"
        self.assertEqual(
            inst_name, general.generate_instance_name("cluster", "worker", 1))
        self.assertEqual(
            inst_name, general.generate_instance_name("CLUSTER", "WORKER", 1))
