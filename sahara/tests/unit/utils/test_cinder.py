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

import mock
from oslo_config import cfg

from sahara import exceptions as ex
from sahara import main
from sahara.tests.unit import base as test_base
from sahara.utils.openstack import cinder


CONF = cfg.CONF


class TestCinder(test_base.SaharaTestCase):
    def setup_context(self, username="test_user", tenant_id="tenant_1",
                      token="test_auth_token", tenant_name='test_tenant',
                      **kwargs):
        self.override_config('os_region_name', 'RegionOne')

        # Fake service_catalog with both volume and volumev2 services available
        service_catalog = '''[
            { "type": "volume",
              "endpoints": [ { "region": "RegionOne",
                               "publicURL": "http://localhost/" } ] },
            { "type": "volumev2",
              "endpoints": [ { "region": "RegionOne",
                               "publicURL": "http://localhost/" } ] } ]'''

        super(TestCinder, self).setup_context(
            username=username, tenant_id=tenant_id, token=token,
            tenant_name=tenant_name, service_catalog=service_catalog, **kwargs)

    @mock.patch('cinderclient.v2.client.Client')
    @mock.patch('cinderclient.v1.client.Client')
    def test_get_cinder_client_api_v1(self, patched1, patched2):
        self.override_config('api_version', 1, group='cinder')
        patched1.return_value = FakeCinderClient(1)
        patched2.return_value = FakeCinderClient(2)

        client = cinder.client()
        self.assertEqual(1, client.client.api_version)

    @mock.patch('cinderclient.v2.client.Client')
    @mock.patch('cinderclient.v1.client.Client')
    def test_get_cinder_client_api_v2(self, patched1, patched2):
        self.override_config('api_version', 2, group='cinder')
        patched1.return_value = FakeCinderClient(1)
        patched2.return_value = FakeCinderClient(2)

        client = cinder.client()
        self.assertEqual(2, client.client.api_version)

    def test_cinder_bad_api_version(self):
        self.override_config('api_version', 0, group='cinder')
        cinder.validate_config()

        # Check bad version falls back to latest supported version
        self.assertEqual(2, main.CONF.cinder.api_version)

    @mock.patch('sahara.utils.openstack.base.url_for')
    def test_check_cinder_exists(self, mock_url_for):
        mock_url_for.return_value = None
        self.assertTrue(cinder.check_cinder_exists())

        mock_url_for.reset_mock()

        mock_url_for.side_effect = ex.SystemError("BANANA")
        self.assertFalse(cinder.check_cinder_exists())


class FakeCinderClient(object):
    def __init__(self, api_version):
        class FakeCinderHTTPClient(object):
            def __init__(self, api_version):
                self.api_version = api_version
        self.client = FakeCinderHTTPClient(api_version)
