# Copyright (c) 2016 Red Hat Inc.
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

from sahara import context
from sahara.db.sqlalchemy import api
from sahara.db.sqlalchemy import models as m
import sahara.tests.unit.base as base


class TestPaginationUtils(testtools.TestCase):

    def test_get_prev_and_next_objects(self):

        query = [mock.MagicMock(id=i) for i in range(100)]

        res = api._get_prev_and_next_objects(query, 5, None)
        self.assertEqual((None, 4), res)

        res = api._get_prev_and_next_objects(query, None, None)
        self.assertEqual((None, None), res)

        res = api._get_prev_and_next_objects(query, 5, mock.MagicMock(id=42))
        self.assertEqual((37, 47), res)

        res = api._get_prev_and_next_objects(query, 5, mock.MagicMock(id=4))
        self.assertEqual((None, 9), res)

        res = api._get_prev_and_next_objects(query, 5, mock.MagicMock(id=100))
        self.assertEqual((None, None), res)

    def test_parse_sorting_args(self):
        self.assertEqual(("name", "desc"), api._parse_sorting_args("-name"))
        self.assertEqual(("name", "asc"), api._parse_sorting_args("name"))


class TestRegex(testtools.TestCase):

    def test_get_regex_op(self):
        regex_op = api._get_regex_op("mysql://user:passw@localhost/sahara")
        self.assertEqual("REGEXP", regex_op)

        regex_op = api._get_regex_op("postgresql://localhost/sahara")
        self.assertEqual("~", regex_op)

        regex_op = api._get_regex_op("sqlite://user:passw@localhost/sahara")
        self.assertIsNone(regex_op)


class TestRegexFilter(base.SaharaWithDbTestCase):

    @mock.patch("sahara.db.sqlalchemy.api._get_regex_op")
    def test_regex_filter(self, get_regex_op):
        query = api.model_query(m.ClusterTemplate, context.ctx())

        regex_cols = ["name", "description", "plugin_name"]
        search_opts = {"name": "fred",
                       "hadoop_version": "2",
                       "bogus": "jack",
                       "plugin_name": "vanilla"}

        # Since regex_op is None remaining_opts should be a copy of search_opts
        get_regex_op.return_value = None
        query, remaining_opts = api.regex_filter(
            query, m.ClusterTemplate, regex_cols, search_opts)
        self.assertEqual(search_opts, remaining_opts)
        self.assertIsNot(search_opts, remaining_opts)

        # Since regex_cols is [] remaining_opts should be a copy of search_opts
        get_regex_op.return_value = "REGEXP"
        query, remaining_opts = api.regex_filter(
            query, m.ClusterTemplate, [], search_opts)
        self.assertEqual(search_opts, remaining_opts)
        self.assertIsNot(search_opts, remaining_opts)

        # Remaining should be search_opts with name and plugin_name removed
        # These are the only fields that are in regex_cols and also in
        # the model.
        get_regex_op.return_value = "REGEXP"
        query, remaining_opts = api.regex_filter(
            query, m.ClusterTemplate, regex_cols, search_opts)
        self.assertEqual({"hadoop_version": "2",
                          "bogus": "jack"}, remaining_opts)

        # bogus is not in the model so it should be left in remaining
        # even though regex_cols lists it
        regex_cols.append("bogus")
        query, remaining_opts = api.regex_filter(
            query, m.ClusterTemplate, regex_cols, search_opts)
        self.assertEqual({"hadoop_version": "2",
                          "bogus": "jack"}, remaining_opts)

        # name will not be removed because the value is not a string
        search_opts["name"] = 5
        query, remaining_opts = api.regex_filter(
            query, m.ClusterTemplate, regex_cols, search_opts)
        self.assertEqual({"hadoop_version": "2",
                          "bogus": "jack",
                          "name": 5}, remaining_opts)
