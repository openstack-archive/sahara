# -*- coding: utf-8 -*-
# Copyright (c) 2014 Adrien Vergé <adrien.verge@numergy.com>
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

from keystoneauth1 import exceptions as keystone_exceptions
from oslo_config import cfg

from sahara import main
from sahara.tests.unit import base as test_base
from sahara.utils.openstack import cinder


CONF = cfg.CONF


class TestCinder(test_base.SaharaTestCase):
    def setup_context(self, username="test_user", tenant_id="tenant_1",
                      token="test_auth_token", tenant_name='test_tenant',
                      **kwargs):
        self.override_config('os_region_name', 'RegionOne')

        service_catalog = '''[
            { "type": "volumev3",
              "endpoints": [ { "region": "RegionOne",
                               "internalURL": "http://localhost/" } ] }]'''

        super(TestCinder, self).setup_context(
            username=username, tenant_id=tenant_id, token=token,
            tenant_name=tenant_name, service_catalog=service_catalog, **kwargs)

    @mock.patch('sahara.utils.openstack.keystone.auth')
    @mock.patch('cinderclient.v3.client.Client')
    def test_get_cinder_client_api_v3(self, patched3, auth):
        self.override_config('api_version', 3, group='cinder')
        patched3.return_value = FakeCinderClient(3)

        client = cinder.client()
        self.assertEqual(3, client.client.api_version)

    def test_cinder_bad_api_version(self):
        self.override_config('api_version', 1, group='cinder')
        cinder.validate_config()

        # Check bad version falls back to latest supported version
        self.assertEqual(3, main.CONF.cinder.api_version)

    @mock.patch('sahara.utils.openstack.base.url_for')
    def test_check_cinder_exists(self, mock_url_for):
        mock_url_for.return_value = None
        self.assertTrue(cinder.check_cinder_exists())

        mock_url_for.reset_mock()

        mock_url_for.side_effect = keystone_exceptions.EndpointNotFound()
        self.assertFalse(cinder.check_cinder_exists())


class FakeCinderClient(object):
    def __init__(self, api_version):
        class FakeCinderHTTPClient(object):
            def __init__(self, api_version):
                self.api_version = api_version
        self.client = FakeCinderHTTPClient(api_version)
