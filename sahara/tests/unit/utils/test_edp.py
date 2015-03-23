# Copyright (c) 2014 Red Hat Inc.
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

from sahara.utils import edp


class SplitJobTypeTest(testtools.TestCase):
    def test_split_job_type(self):
        jtype, stype = edp.split_job_type(edp.JOB_TYPE_MAPREDUCE)
        self.assertEqual(edp.JOB_TYPE_MAPREDUCE, jtype)
        self.assertEqual(edp.JOB_SUBTYPE_NONE, stype)

        jtype, stype = edp.split_job_type(edp.JOB_TYPE_MAPREDUCE_STREAMING)
        self.assertEqual(edp.JOB_TYPE_MAPREDUCE, jtype)
        self.assertEqual(edp.JOB_SUBTYPE_STREAMING, stype)

    def test_compare_job_type(self):
        self.assertTrue(edp.compare_job_type(
            edp.JOB_TYPE_JAVA,
            edp.JOB_TYPE_JAVA,
            edp.JOB_TYPE_MAPREDUCE,
            strict=True))
        self.assertFalse(edp.compare_job_type(
            edp.JOB_TYPE_MAPREDUCE_STREAMING,
            edp.JOB_TYPE_JAVA,
            edp.JOB_TYPE_MAPREDUCE,
            strict=True))
        self.assertTrue(edp.compare_job_type(
            edp.JOB_TYPE_MAPREDUCE_STREAMING,
            edp.JOB_TYPE_JAVA,
            edp.JOB_TYPE_MAPREDUCE))
        self.assertFalse(edp.compare_job_type(
            edp.JOB_TYPE_MAPREDUCE,
            edp.JOB_TYPE_JAVA,
            edp.JOB_TYPE_MAPREDUCE_STREAMING))
