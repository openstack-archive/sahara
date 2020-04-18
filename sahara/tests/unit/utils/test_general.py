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

from unittest import mock

from sahara.tests.unit import base
from sahara.utils import general


class UtilsGeneralTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(UtilsGeneralTest, self).setUp()

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
        self.assertIsNone(general.find_dict(iterable, z=4))

    def test_find(self):
        lst = [mock.Mock(a=5), mock.Mock(b=5), mock.Mock(a=7, b=7)]
        self.assertEqual(lst[0], general.find(lst, a=5))
        self.assertEqual(lst[1], general.find(lst, b=5))
        self.assertIsNone(general.find(lst, a=8))
        self.assertEqual(lst[2], general.find(lst, a=7))
        self.assertEqual(lst[2], general.find(lst, a=7, b=7))

    def test_generate_instance_name(self):
        inst_name = "cluster-worker-001"
        self.assertEqual(
            inst_name, general.generate_instance_name("cluster", "worker", 1))
        self.assertEqual(
            inst_name, general.generate_instance_name("CLUSTER", "WORKER", 1))

    def test_get_by_id(self):
        lst = [mock.Mock(id=5), mock.Mock(id=7)]
        self.assertIsNone(general.get_by_id(lst, 9))
        self.assertEqual(lst[0], general.get_by_id(lst, 5))
        self.assertEqual(lst[1], general.get_by_id(lst, 7))

    def test_natural_sort_key(self):
        str_test = "ABC123efg345DD"
        str_list = ['abc', 123, 'efg', 345, 'dd']
        str_sort = general.natural_sort_key(str_test)
        self.assertEqual(len(str_list), len(str_sort))

        self.assertEqual(str_list, str_sort)
