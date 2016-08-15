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

from sahara import context
from sahara.plugins import kerberos as krb
from sahara.tests.unit import base


class FakeObject(dict):
    def __init__(self, dict):
        self._dict = dict
        super(FakeObject, self).__init__(**dict)

    def to_dict(self):
        return self._dict


class TestKerberosBase(base.SaharaTestCase):
    def test_list_configs(self):
        self.assertEqual(7, len(krb.get_config_list()))

    @mock.patch('sahara.conductor.API.cluster_update')
    @mock.patch('sahara.conductor.API.cluster_get')
    @mock.patch('sahara.service.castellan.utils.store_secret')
    @mock.patch('sahara.service.castellan.utils.get_secret')
    def test_get_server_password(
            self, get_secret, store_secret, cluster_get_mock,
            cluster_update_mock):
        cl = mock.Mock(
            node_groups=[], cluster_configs={}, extra={})
        ctx = context.ctx()
        cluster_get_mock.return_value = cl
        store_secret.return_value = 'secret-id'
        krb.get_server_password(cl)

        self.assertEqual(1, cluster_get_mock.call_count)
        self.assertEqual(1, cluster_update_mock.call_count)
        self.assertEqual([
            mock.call(ctx, cl, {'extra': {'admin-passwd-kdc': 'secret-id'}})],
            cluster_update_mock.call_args_list)

        self.assertEqual(1, get_secret.call_count)
        self.assertEqual(1, store_secret.call_count)

        cl = mock.Mock(
            node_groups=[], cluster_configs={},
            extra=FakeObject({'admin-passwd-kdc': 'secret-id'}))
        cluster_get_mock.return_value = cl
        krb.get_server_password(cl)

        self.assertEqual(2, get_secret.call_count)
        self.assertEqual(1, store_secret.call_count)
        self.assertEqual(1, cluster_update_mock.call_count)

        cl = mock.Mock(
            node_groups=[], cluster_configs=FakeObject({
                'Existing KDC': True, 'Admin password': 'THE BEST EVER'}),
            extra=FakeObject({'admin-passwd-kdc': 'secret-id'}))
        cluster_get_mock.return_value = cl
        get_secret.return_value = 'THE BEST EVER'
        self.assertEqual('THE BEST EVER', krb.get_server_password(cl))

    def test_base_configs(self):
        cluster = mock.Mock(
            cluster_configs={'Kerberos': {'Enable Kerberos Security': True}},
            node_groups=[],
        )
        self.assertTrue(krb.is_kerberos_security_enabled(cluster))

        cluster = mock.Mock(
            cluster_configs={'Kerberos': {'Enable Kerberos Security': False}},
            node_groups=[],
        )
        self.assertFalse(krb.is_kerberos_security_enabled(cluster))

    @mock.patch('sahara.plugins.kerberos.get_server_password')
    def test_get_server_installation_script(self, get):
        cluster = mock.Mock(node_groups=[], cluster_configs={})
        get.return_value = 'password'
        krb._get_server_installation_script(
            cluster, 'server.novalocal', 'centos', '6.7')
