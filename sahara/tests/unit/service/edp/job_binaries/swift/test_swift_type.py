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
from unittest import mock

import sahara.exceptions as ex
from sahara.service.castellan import config as castellan
from sahara.service.edp.job_binaries.swift.implementation import SwiftType
from sahara.tests.unit import base


class TestSwiftType(base.SaharaTestCase):

    def setUp(self):
        super(TestSwiftType, self).setUp()
        castellan.validate_config()
        self.i_s = SwiftType()

    def test_validate_job_location_format(self):
        self.assertFalse(self.i_s.validate_job_location_format(''))
        self.assertFalse(self.i_s.validate_job_location_format('swift://'))
        self.assertTrue(self.i_s.
                        validate_job_location_format('swift://123'))

    def test_validate(self):
        data = {}
        self.i_s.validate(data, job_binary_id='id')

        with testtools.ExpectedException(ex.BadJobBinaryException):
            self.i_s.validate(data)

        self.override_config('use_domain_for_proxy_users', True)
        self.i_s.validate(data)

        self.override_config('use_domain_for_proxy_users', False)
        data = {
            "extra": {
                "user": "user",
                "password": "pass"
            }
        }
        self.i_s.validate(data)

    @mock.patch('sahara.service.edp.job_binaries.'
                'swift.implementation.SwiftType.get_raw_data')
    def test_copy_binary_to_cluster(self, get_raw_data):
        remote = mock.Mock()
        job_binary = mock.Mock()
        job_binary.name = 'test'
        job_binary.url = 'swift://somebinary'
        get_raw_data.return_value = 'test'

        res = self.i_s.copy_binary_to_cluster(job_binary,
                                              remote=remote)

        self.assertEqual('/tmp/test', res)
        remote.write_file_to.assert_called_with(
            '/tmp/test',
            'test')

    def test__get_raw_data(self):
        client_instance = mock.Mock()
        client_instance.head_object = mock.Mock()
        client_instance.get_object = mock.Mock()

        job_binary = mock.Mock()
        job_binary.url = 'swift://container/object'

        # an object that is too large should raise an exception
        header = {'content-length': '2048'}
        client_instance.head_object.return_value = header
        self.override_config('job_binary_max_KB', 1)
        self.assertRaises(ex.DataTooBigException,
                          self.i_s._get_raw_data,
                          job_binary, client_instance)
        client_instance.head_object.assert_called_once_with('container',
                                                            'object')

        # valid return
        header = {'content-length': '4'}
        body = 'data'
        client_instance.head_object.return_value = header
        client_instance.get_object.return_value = (header, body)
        self.assertEqual(body, self.i_s._get_raw_data(job_binary,
                         client_instance))
        client_instance.get_object.assert_called_once_with('container',
                                                           'object')

    def test_validate_job_binary_url(self):

        job_binary = mock.Mock()

        # bad swift url should raise an exception
        job_binary.url = 'notswift://container/object'
        with testtools.ExpectedException(ex.BadJobBinaryException):
            self.i_s._validate_job_binary_url(job_binary)

        # specifying only a container should raise an exception
        job_binary.url = 'swift://container'
        with testtools.ExpectedException(ex.BadJobBinaryException):
            self.i_s._validate_job_binary_url(job_binary)

        job_binary.url = 'swift://container/path'
        self.i_s._validate_job_binary_url(job_binary)

    @mock.patch('sahara.service.edp.job_binaries.swift.implementation.'
                'SwiftType._get_raw_data')
    @mock.patch('sahara.utils.openstack.swift.client')
    def test_get_raw_data(self, swift_client, get_raw_data):
        client_instance = mock.Mock()
        swift_client.return_value = client_instance

        job_binary = mock.Mock()
        job_binary.url = 'swift://container/object'

        # embedded credentials
        job_binary.extra = dict(user='test', password='secret')
        self.i_s.get_raw_data(job_binary)
        swift_client.assert_called_with(username='test',
                                        password='secret')
        get_raw_data.assert_called_with(job_binary, client_instance)

        # proxy configs should override embedded credentials
        proxy_configs = dict(proxy_username='proxytest',
                             proxy_password='proxysecret',
                             proxy_trust_id='proxytrust')
        self.i_s.get_raw_data(job_binary, proxy_configs=proxy_configs)
        swift_client.assert_called_with(username='proxytest',
                                        password='proxysecret',
                                        trust_id='proxytrust')
        get_raw_data.assert_called_with(job_binary, client_instance)

    @mock.patch('sahara.utils.openstack.base.url_for')
    @mock.patch('sahara.context.ctx')
    @mock.patch(
        'sahara.service.edp.job_binaries.swift.'
        'implementation.SwiftType._get_raw_data')
    @mock.patch('swiftclient.Connection')
    def test_get_raw_data_with_context(self, swift_client, _get_raw_data, ctx,
                                       url_for):
        client_instance = mock.Mock()
        swift_client.return_value = client_instance
        test_context = mock.Mock()
        test_context.auth_token = 'testtoken'
        test_context.auth_plugin = None
        ctx.return_value = test_context
        url_for.return_value = 'url_for'
        job_binary = mock.Mock()
        job_binary.url = 'swift://container/object'

        job_binary.extra = dict(user='test', password='secret')
        self.i_s.get_raw_data(job_binary, with_context=True)
        self.assertEqual([mock.call(
            auth_version='3',
            cacert=None, insecure=False,
            max_backoff=10,
            preauthtoken='testtoken',
            preauthurl='url_for', retries=5,
            retry_on_ratelimit=True, starting_backoff=10)],
            swift_client.call_args_list)
        _get_raw_data.assert_called_with(job_binary, client_instance)
