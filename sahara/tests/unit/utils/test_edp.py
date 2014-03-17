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

import unittest2

from sahara.utils import edp


MAPRED_STREAMING = "MapReduce" + edp.JOB_TYPE_SEP + "Streaming"


class SplitJobTypeTest(unittest2.TestCase):
    def test_split_job_type(self):
        jtype, stype = edp.split_job_type("MapReduce")
        self.assertEqual(jtype, "MapReduce")
        self.assertEqual(stype, "")

        jtype, stype = edp.split_job_type(MAPRED_STREAMING)
        self.assertEqual(jtype, "MapReduce")
        self.assertEqual(stype, "Streaming")

    def test_compare_job_type(self):
        self.assertTrue(edp.compare_job_type("Java",
                                             "Java", "MapReduce",
                                             strict=True))
        self.assertFalse(edp.compare_job_type(MAPRED_STREAMING,
                                              "Java", "MapReduce",
                                              strict=True))
        self.assertTrue(edp.compare_job_type(MAPRED_STREAMING,
                                             "Java", "MapReduce"))
        self.assertFalse(edp.compare_job_type("MapReduce",
                                              "Java", MAPRED_STREAMING))
