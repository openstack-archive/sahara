# Copyright (c) 2014 Mirantis Inc.
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

from cinderclient import exceptions as cinder_exc
from heatclient import exc as heat_exc
from keystoneauth1 import exceptions as keystone_exc
from neutronclient.common import exceptions as neutron_exc
from novaclient import exceptions as nova_exc

from sahara import exceptions as sahara_exc
from sahara.tests.unit import base as testbase
from sahara.utils.openstack import base


class TestBase(testbase.SaharaTestCase):

    def test_url_for_regions(self):
        service_catalog = (
            '[{"endpoints": '
            '  [{"adminURL": "http://192.168.0.5:8774/v2", '
            '    "region": "RegionOne", '
            '    "id": "83d12c9ad2d647ecab7cbe91adb8666b", '
            '    "internalURL": "http://192.168.0.5:8774/v2", '
            '    "publicURL": "http://172.18.184.5:8774/v2"}, '
            '   {"adminURL": "http://192.168.0.6:8774/v2", '
            '    "region": "RegionTwo", '
            '    "id": "07c5a555176246c783d8f0497c98537b", '
            '    "internalURL": "http://192.168.0.6:8774/v2", '
            '    "publicURL": "http://172.18.184.6:8774/v2"}], '
            '  "endpoints_links": [], '
            '  "type": "compute", '
            '  "name": "nova"}]')

        self.override_config("os_region_name", "RegionOne")
        self.assertEqual("http://192.168.0.5:8774/v2",
                         base.url_for(service_catalog, "compute"))

        self.override_config("os_region_name", "RegionTwo")
        self.assertEqual("http://192.168.0.6:8774/v2",
                         base.url_for(service_catalog, "compute"))


class AuthUrlTest(testbase.SaharaTestCase):

    def test_retrieve_auth_url_api_v3(self):
        self.override_config('use_identity_api_v3', True)
        correct = "https://127.0.0.1:8080/v3"

        def _assert(uri):
            self.override_config('auth_url', uri, 'trustee')
            self.assertEqual(correct, base.retrieve_auth_url())

        _assert("%s/" % correct)
        _assert("https://127.0.0.1:8080")
        _assert("https://127.0.0.1:8080/")
        _assert("https://127.0.0.1:8080/v2.0")
        _assert("https://127.0.0.1:8080/v2.0/")
        _assert("https://127.0.0.1:8080/v3")
        _assert("https://127.0.0.1:8080/v3/")

    @mock.patch("sahara.utils.openstack.base.url_for")
    def test_retrieve_auth_url_api_v3_without_port(self, mock_url_for):
        self.override_config('use_identity_api_v3', True)
        self.setup_context(service_catalog=True)
        correct = "https://127.0.0.1/v3"

        def _assert(uri):
            mock_url_for.return_value = uri
            self.assertEqual(correct, base.retrieve_auth_url())

        _assert("%s/" % correct)
        _assert("https://127.0.0.1")
        _assert("https://127.0.0.1/")
        _assert("https://127.0.0.1/v2.0")
        _assert("https://127.0.0.1/v2.0/")
        _assert("https://127.0.0.1/v3")
        _assert("https://127.0.0.1/v3/")

    @mock.patch("sahara.utils.openstack.base.url_for")
    def test_retrieve_auth_url_api_v3_path_present(self, mock_url_for):
        self.override_config('use_identity_api_v3', True)
        self.setup_context(service_catalog=True)
        correct = "https://127.0.0.1/identity/v3"

        def _assert(uri):
            mock_url_for.return_value = uri
            self.assertEqual(correct, base.retrieve_auth_url())

        _assert("%s" % correct)
        _assert("%s/" % correct)
        _assert("https://127.0.0.1/identity")
        _assert("https://127.0.0.1/identity/")

    def test_retrieve_auth_url_api_v20(self):
        self.override_config('use_identity_api_v3', False)
        correct = "https://127.0.0.1:8080/v2.0"

        def _assert(uri):
            self.override_config('auth_url', uri, 'trustee')
            self.assertEqual(correct, base.retrieve_auth_url())

        _assert("%s/" % correct)
        _assert("https://127.0.0.1:8080")
        _assert("https://127.0.0.1:8080/")
        _assert("https://127.0.0.1:8080/v2.0")
        _assert("https://127.0.0.1:8080/v2.0/")
        _assert("https://127.0.0.1:8080/v3")
        _assert("https://127.0.0.1:8080/v3/")

    @mock.patch("sahara.utils.openstack.base.url_for")
    def test_retrieve_auth_url_api_v20_without_port(self, mock_url_for):
        self.override_config('use_identity_api_v3', False)
        self.setup_context(service_catalog=True)
        correct = "https://127.0.0.1/v2.0"

        def _assert(uri):
            mock_url_for.return_value = uri
            self.assertEqual(correct, base.retrieve_auth_url())

        _assert("%s/" % correct)
        _assert("https://127.0.0.1")
        _assert("https://127.0.0.1/")
        _assert("https://127.0.0.1/v2.0")
        _assert("https://127.0.0.1/v2.0/")
        _assert("https://127.0.0.1/v3")
        _assert("https://127.0.0.1/v3/")


class ExecuteWithRetryTest(testbase.SaharaTestCase):

    def setUp(self):
        super(ExecuteWithRetryTest, self).setUp()
        self.fake_client_call = mock.MagicMock()
        self.fake_client_call.__name__ = 'fake_client_call'
        self.override_config('retries_number', 2, 'retries')

    @mock.patch('sahara.context.sleep')
    def _check_error_without_retry(self, error, code, m_sleep):
        self.fake_client_call.side_effect = error(code)

        self.assertRaises(error, base.execute_with_retries,
                          self.fake_client_call)
        self.assertEqual(1, self.fake_client_call.call_count)
        self.fake_client_call.reset_mock()

    @mock.patch('sahara.context.sleep')
    def _check_error_with_retry(self, error, code, m_sleep):
        self.fake_client_call.side_effect = error(code)

        self.assertRaises(sahara_exc.MaxRetriesExceeded,
                          base.execute_with_retries, self.fake_client_call)
        self.assertEqual(3, self.fake_client_call.call_count)
        self.fake_client_call.reset_mock()

    def test_novaclient_calls_without_retry(self):
        # check that following errors will not be retried
        self._check_error_without_retry(nova_exc.BadRequest, 400)
        self._check_error_without_retry(nova_exc.Unauthorized, 401)
        self._check_error_without_retry(nova_exc.Forbidden, 403)
        self._check_error_without_retry(nova_exc.NotFound, 404)
        self._check_error_without_retry(nova_exc.MethodNotAllowed, 405)
        self._check_error_without_retry(nova_exc.Conflict, 409)
        self._check_error_without_retry(nova_exc.HTTPNotImplemented, 501)

    def test_novaclient_calls_with_retry(self):
        # check that following errors will be retried
        self._check_error_with_retry(nova_exc.OverLimit, 413)
        self._check_error_with_retry(nova_exc.RateLimit, 429)

    def test_cinderclient_calls_without_retry(self):
        # check that following errors will not be retried
        self._check_error_without_retry(cinder_exc.BadRequest, 400)
        self._check_error_without_retry(cinder_exc.Unauthorized, 401)
        self._check_error_without_retry(cinder_exc.Forbidden, 403)
        self._check_error_without_retry(cinder_exc.NotFound, 404)
        self._check_error_without_retry(nova_exc.HTTPNotImplemented, 501)

    def test_cinderclient_calls_with_retry(self):
        # check that following error will be retried
        self._check_error_with_retry(cinder_exc.OverLimit, 413)

    def test_neutronclient_calls_without_retry(self):
        # check that following errors will not be retried
        # neutron exception expects string in constructor
        self._check_error_without_retry(neutron_exc.BadRequest, "400")
        self._check_error_without_retry(neutron_exc.Forbidden, "403")
        self._check_error_without_retry(neutron_exc.NotFound, "404")
        self._check_error_without_retry(neutron_exc.Conflict, "409")

    def test_neutronclient_calls_with_retry(self):
        # check that following errors will be retried
        # neutron exception expects string in constructor
        self._check_error_with_retry(neutron_exc.InternalServerError, "500")
        self._check_error_with_retry(neutron_exc.ServiceUnavailable, "503")

    def test_heatclient_calls_without_retry(self):
        # check that following errors will not be retried
        self._check_error_without_retry(heat_exc.HTTPBadRequest, 400)
        self._check_error_without_retry(heat_exc.HTTPUnauthorized, 401)
        self._check_error_without_retry(heat_exc.HTTPForbidden, 403)
        self._check_error_without_retry(heat_exc.HTTPNotFound, 404)
        self._check_error_without_retry(heat_exc.HTTPMethodNotAllowed, 405)
        self._check_error_without_retry(heat_exc.HTTPConflict, 409)
        self._check_error_without_retry(heat_exc.HTTPUnsupported, 415)
        self._check_error_without_retry(heat_exc.HTTPNotImplemented, 501)

    def test_heatclient_calls_with_retry(self):
        # check that following errors will be retried
        self._check_error_with_retry(heat_exc.HTTPInternalServerError, 500)
        self._check_error_with_retry(heat_exc.HTTPBadGateway, 502)
        self._check_error_with_retry(heat_exc.HTTPServiceUnavailable, 503)

    def test_keystoneclient_calls_without_retry(self):
        # check that following errors will not be retried
        self._check_error_without_retry(keystone_exc.BadRequest, 400)
        self._check_error_without_retry(keystone_exc.Unauthorized, 401)
        self._check_error_without_retry(keystone_exc.Forbidden, 403)
        self._check_error_without_retry(keystone_exc.NotFound, 404)
        self._check_error_without_retry(keystone_exc.MethodNotAllowed, 405)
        self._check_error_without_retry(keystone_exc.Conflict, 409)
        self._check_error_without_retry(keystone_exc.UnsupportedMediaType, 415)
        self._check_error_without_retry(keystone_exc.HttpNotImplemented, 501)

    def test_keystoneclient_calls_with_retry(self):
        # check that following errors will be retried
        self._check_error_with_retry(keystone_exc.RequestTimeout, 408)
        self._check_error_with_retry(keystone_exc.InternalServerError, 500)
        self._check_error_with_retry(keystone_exc.BadGateway, 502)
        self._check_error_with_retry(keystone_exc.ServiceUnavailable, 503)
        self._check_error_with_retry(keystone_exc.GatewayTimeout, 504)
