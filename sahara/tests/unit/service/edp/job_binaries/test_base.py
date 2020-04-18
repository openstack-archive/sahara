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

from sahara.service.edp.job_binaries import base as jb_base
from sahara.tests.unit import base


class _FakeJobBinary(jb_base.JobBinaryType):
    def copy_binary_to_cluster(self, job_binary, **kwargs):
        return 'valid path'


class JobBinaryManagerSupportTest(base.SaharaTestCase):

    def setUp(self):
        super(JobBinaryManagerSupportTest, self).setUp()
        self.job_binary = _FakeJobBinary()

    def test_generate_valid_path(self):
        jb = mock.Mock()
        jb.name = 'jb_name.jar'
        res = self.job_binary._generate_valid_path(jb)
        self.assertEqual('/tmp/jb_name.jar', res)
