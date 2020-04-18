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

import copy
from unittest import mock

from oslo_utils import uuidutils
import testtools

import sahara.exceptions as ex
from sahara.service.edp.data_sources.swift.implementation import SwiftType
from sahara.service.edp import job_utils
from sahara.swift import utils as su
from sahara.tests.unit import base
from sahara.tests.unit.service.edp import edp_test_utils as u
from sahara.utils.types import FrozenDict

SAMPLE_SWIFT_URL = "swift://1234/object"
SAMPLE_SWIFT_URL_WITH_SUFFIX = "swift://1234%s/object" % su.SWIFT_URL_SUFFIX


class TestSwiftTypeValidation(base.SaharaTestCase):
    def setUp(self):
        super(TestSwiftTypeValidation, self).setUp()
        self.s_type = SwiftType()

    @mock.patch('sahara.context.ctx')
    def test_prepare_cluster(self, ctx):

        ctx.return_value = 'dummy'

        ds_url = "swift://container/input"
        ds = u.create_data_source(ds_url,
                                  name="data_source",
                                  id=uuidutils.generate_uuid())

        job_configs = {
            'configs': {
                job_utils.DATA_SOURCE_SUBST_NAME: True,
                job_utils.DATA_SOURCE_SUBST_UUID: True
                }
            }

        old_configs = copy.deepcopy(job_configs)

        self.s_type.prepare_cluster(ds, u.create_cluster(),
                                    job_configs=job_configs)
        # Swift configs should be filled in since they were blank
        self.assertEqual(ds.credentials['user'],
                         job_configs['configs']
                         ['fs.swift.service.sahara.username'])
        self.assertEqual(ds.credentials['password'],
                         job_configs['configs']
                         ['fs.swift.service.sahara.password'])

        self.assertNotEqual(old_configs, job_configs)

        job_configs['configs'] = {'fs.swift.service.sahara.username': 'sam',
                                  'fs.swift.service.sahara.password': 'gamgee',
                                  job_utils.DATA_SOURCE_SUBST_NAME: False,
                                  job_utils.DATA_SOURCE_SUBST_UUID: True}
        old_configs = copy.deepcopy(job_configs)

        self.s_type.prepare_cluster(ds, u.create_cluster(),
                                    job_configs=job_configs)
        # Swift configs should not be overwritten
        self.assertEqual(old_configs['configs'], job_configs['configs'])

        job_configs['configs'] = {job_utils.DATA_SOURCE_SUBST_NAME: True,
                                  job_utils.DATA_SOURCE_SUBST_UUID: False}
        job_configs['proxy_configs'] = {'proxy_username': 'john',
                                        'proxy_password': 'smith',
                                        'proxy_trust_id': 'trustme'}
        old_configs = copy.deepcopy(job_configs)
        self.s_type.prepare_cluster(ds, u.create_cluster(),
                                    job_configs=job_configs)

        # Swift configs should be empty and proxy configs should be preserved
        self.assertEqual(old_configs['configs'], job_configs['configs'])
        self.assertEqual(old_configs['proxy_configs'],
                         job_configs['proxy_configs'])

        # If there's no configs do nothing
        job_configs['configs'] = None
        old_configs = copy.deepcopy(job_configs)

        self.s_type.prepare_cluster(ds, u.create_cluster(),
                                    job_configs=job_configs)
        self.assertEqual(old_configs, job_configs)

        # If it's a FrozenDict do nothing
        job_configs = {
            'configs': {
                job_utils.DATA_SOURCE_SUBST_NAME: True,
                job_utils.DATA_SOURCE_SUBST_UUID: True
                }
            }

        old_configs = copy.deepcopy(job_configs)
        job_configs = FrozenDict(job_configs)

        self.s_type.prepare_cluster(ds, u.create_cluster(),
                                    job_configs=job_configs)
        self.assertEqual(old_configs, job_configs)

    def test_swift_type_validation(self):
        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "credentials": {
                "user": "user",
                "password": "password"
            },
            "description": "long description"
        }
        self.s_type.validate(data)

    def test_swift_type_validation_missing_credentials(self):
        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "description": "long description"
        }
        with testtools.ExpectedException(ex.InvalidCredentials):
            self.s_type.validate(data)
        # proxy enabled should allow creation without credentials
        self.override_config('use_domain_for_proxy_users', True)
        self.s_type.validate(data)

    def test_swift_type_validation_credentials_missing_user(self):
        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "credentials": {
                "password": "password"
            },
            "description": "long description"
        }
        with testtools.ExpectedException(ex.InvalidCredentials):
            self.s_type.validate(data)
        # proxy enabled should allow creation without credentials
        self.override_config('use_domain_for_proxy_users', True)
        self.s_type.validate(data)

    def test_swift_type_validation_credentials_missing_password(self):
        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL,
            "type": "swift",
            "credentials": {
                "user": "user",
            },
            "description": "long description"
        }
        with testtools.ExpectedException(ex.InvalidCredentials):
            self.s_type.validate(data)
        # proxy enabled should allow creation without credentials
        self.override_config('use_domain_for_proxy_users', True)
        self.s_type.validate(data)

    def test_swift_type_validation_wrong_schema(self):
        data = {
            "name": "test_data_data_source",
            "url": "swif://1234/object",
            "type": "swift",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type.validate(data)

    def test_swift_type_validation_explicit_suffix(self):
        data = {
            "name": "test_data_data_source",
            "url": SAMPLE_SWIFT_URL_WITH_SUFFIX,
            "type": "swift",
            "description": "incorrect url schema",
            "credentials": {
                "user": "user",
                "password": "password"
            }
        }
        self.s_type.validate(data)

    def test_swift_type_validation_wrong_suffix(self):
        data = {
            "name": "test_data_data_source",
            "url": "swift://1234.suffix/object",
            "type": "swift",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type.validate(data)

    def test_swift_type_validation_missing_object(self):
        data = {
            "name": "test_data_data_source",
            "url": "swift://1234/",
            "type": "swift",
            "description": "incorrect url schema"
        }
        with testtools.ExpectedException(ex.InvalidDataException):
            self.s_type.validate(data)
