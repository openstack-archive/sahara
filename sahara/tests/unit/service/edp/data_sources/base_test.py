# Copyright (c) 2017 OpenStack Foundation
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

from oslo_utils import uuidutils

from sahara.service.edp.data_sources.base import DataSourceType

import testtools


class DataSourceBaseTestCase(testtools.TestCase):
    def setUp(self):
        super(DataSourceBaseTestCase, self).setUp()
        self.ds_base = DataSourceType()

    def test_construct_url_no_placeholders(self):
        base_url = "swift://container/input"
        job_exec_id = uuidutils.generate_uuid()

        url = self.ds_base.construct_url(base_url, job_exec_id)

        self.assertEqual(base_url, url)

    def test_construct_url_job_exec_id_placeholder(self):
        base_url = "swift://container/input.%JOB_EXEC_ID%.out"
        job_exec_id = uuidutils.generate_uuid()

        url = self.ds_base.construct_url(base_url, job_exec_id)

        self.assertEqual(
            "swift://container/input." + job_exec_id + ".out", url)

    def test_construct_url_randstr_placeholder(self):
        base_url = "swift://container/input.%RANDSTR(4)%.%RANDSTR(7)%.out"
        job_exec_id = uuidutils.generate_uuid()

        url = self.ds_base.construct_url(base_url, job_exec_id)

        self.assertRegex(
            url, "swift://container/input\.[a-z]{4}\.[a-z]{7}\.out")

    def test_construct_url_randstr_and_job_exec_id_placeholder(self):
        base_url = "swift://container/input.%JOB_EXEC_ID%.%RANDSTR(7)%.out"
        job_exec_id = uuidutils.generate_uuid()

        url = self.ds_base.construct_url(base_url, job_exec_id)

        self.assertRegex(
            url, "swift://container/input." + job_exec_id + "\.[a-z]{7}\.out")

    def test_get_urls(self):
        url = 'test://url'
        cluster = mock.Mock()
        job_exec_id = 'test_id'

        self.assertEqual((url, url), self.ds_base.get_urls(url,
                         cluster, job_exec_id))
