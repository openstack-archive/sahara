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

import sqlalchemy as sa
import unittest2

from savanna.db.sqlalchemy import types


class JsonEncodedTest(unittest2.TestCase):
    def test_impl(self):
        impl = types.JsonEncoded.impl
        self.assertTrue(impl.hashable)
        self.assertEqual(sa.Text, impl)

    def test_process_bind_param(self):
        t = types.JsonEncoded()
        self.assertEqual('{"a": 1}', t.process_bind_param({"a": 1}, None))

    def test_process_bind_param_none(self):
        t = types.JsonEncoded()
        self.assertIsNone(t.process_bind_param(None, None))

    def test_process_result_value(self):
        t = types.JsonEncoded()
        self.assertEqual({"a": 1}, t.process_result_value('{"a": 1}', None))

    def test_process_result_value_none(self):
        t = types.JsonEncoded()
        self.assertIsNone(t.process_result_value(None, None))
