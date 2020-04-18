# Copyright (c) 2016 Mirantis Inc.
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

from sahara import exceptions
from sahara.service import validation
from sahara.tests.unit import base


class TestValidation(base.SaharaTestCase):
    def test_get_path(self):
        self.assertEqual('', validation._get_path([]))
        self.assertEqual('param: ', validation._get_path(['param']))
        self.assertEqual(
            'param[0][id]: ', validation._get_path(['param', 0, 'id']))

    def test_generate_error(self):
        # no errors occurred during validation
        self.assertIsNone(validation._generate_error([]))

        # one error occurred during validation
        err = mock.Mock(message='some error', path=['param'])
        generated_err = validation._generate_error([err])
        self.assertIsInstance(generated_err, exceptions.SaharaException)
        self.assertEqual('VALIDATION_ERROR', generated_err.code)
        self.assertIn('param: some error', generated_err.message)

        # several errors occurred during validation
        errors = [mock.Mock(message='first error', path=['param1']),
                  mock.Mock(
                      message='second error', path=['param2', 0, 'subparam'])]
        generated_err = validation._generate_error(errors)
        self.assertIsInstance(generated_err, exceptions.SaharaException)
        self.assertEqual('VALIDATION_ERROR', generated_err.code)
        self.assertIn('param1: first error\nparam2[0][subparam]: second error',
                      generated_err.message)
