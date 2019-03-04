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

import testtools

import sahara.exceptions as ex
from sahara.service.edp.job_binaries import manager as jb_manager
from sahara.tests.unit import base


class JobBinaryManagerSupportTest(base.SaharaTestCase):

    def setUp(self):
        super(JobBinaryManagerSupportTest, self).setUp()
        jb_manager.setup_job_binaries()

    def test_job_binaries_loaded(self):
        jb_types = [jb.name for jb in
                    jb_manager.JOB_BINARIES.get_job_binaries()]

        self.assertIn('internal-db', jb_types)
        self.assertIn('manila', jb_types)
        self.assertIn('swift', jb_types)

    def test_get_job_binary_by_url(self):

        with testtools.ExpectedException(ex.InvalidDataException):
            jb_manager.JOB_BINARIES.get_job_binary_by_url('')

        with testtools.ExpectedException(ex.InvalidDataException):
            jb_manager.JOB_BINARIES.get_job_binary_by_url('internal-db')

        self.assertEqual('internal-db', jb_manager.JOB_BINARIES
                         .get_job_binary_by_url('internal-db://').name)

        self.assertEqual('manila', jb_manager.JOB_BINARIES
                         .get_job_binary_by_url('manila://').name)

        self.assertEqual('swift', jb_manager.JOB_BINARIES
                         .get_job_binary_by_url('swift://').name)

    def test_get_job_binary(self):

        with testtools.ExpectedException(ex.InvalidDataException):
            jb_manager.JOB_BINARIES.get_job_binary('')

        with testtools.ExpectedException(ex.InvalidDataException):
            jb_manager.JOB_BINARIES.get_job_binary('internaldb')

        self.assertEqual('internal-db', jb_manager.JOB_BINARIES
                         .get_job_binary('internal-db').name)

        self.assertEqual('manila', jb_manager.JOB_BINARIES
                         .get_job_binary('manila').name)

        self.assertEqual('swift', jb_manager.JOB_BINARIES
                         .get_job_binary('swift').name)
