# Copyright (c) 2014 Red Hat, Inc.
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

import mock

import sahara.exceptions as ex
from sahara.service.edp.binary_retrievers import internal_swift as i_s
from sahara.tests.unit import base


class TestInternalSwift(base.SaharaTestCase):
    def setUp(self):
        super(TestInternalSwift, self).setUp()

    @mock.patch('sahara.utils.openstack.swift.client')
    def test_get_raw_data(self, swift_client):
        client_instance = mock.Mock()
        swift_client.return_value = client_instance

        job_binary = mock.Mock()
        job_binary.extra = dict(user='test', password='secret')

        # bad swift url should raise an exception
        job_binary.url = 'notswift://container/object'
        self.assertRaises(ex.BadJobBinaryException,
                          i_s.get_raw_data,
                          job_binary)

        # specifying a container should raise an exception
        job_binary.url = 'swift://container'
        self.assertRaises(ex.BadJobBinaryException,
                          i_s.get_raw_data,
                          job_binary)

        # an object that is too large should raise an exception
        job_binary.url = 'swift://container/object'
        client_instance.head_object = mock.Mock()
        header = {'content-length': '2048'}
        client_instance.head_object.return_value = header
        self.override_config('job_binary_max_KB', 1)
        self.assertRaises(ex.DataTooBigException,
                          i_s.get_raw_data,
                          job_binary)
        client_instance.head_object.assert_called_once_with('container',
                                                            'object')

        # valid return
        client_instance.get_object = mock.Mock()
        header = {'content-length': '4'}
        body = 'data'
        client_instance.head_object.return_value = header
        client_instance.get_object.return_value = (header, body)
        self.assertEqual(body, i_s.get_raw_data(job_binary))
        client_instance.get_object.assert_called_once_with('container',
                                                           'object')
