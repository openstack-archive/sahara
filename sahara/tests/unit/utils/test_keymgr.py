# Copyright (c) 2015 Red Hat, Inc.
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

from sahara.tests.unit import base
from sahara.utils import keymgr


class TestKeymgrUtils(base.SaharaTestCase):
    def setUp(self):
        super(TestKeymgrUtils, self).setUp()

    @mock.patch('sahara.utils.openstack.barbican.client_for_admin')
    def test_keymgr_delete_with_external(self, client_for_admin):
        self.override_config('use_external_key_manager', True)
        keyref = 'test_key_reference'
        secrets_manager = mock.Mock()
        secrets_manager.delete = mock.Mock()
        client = mock.Mock(secrets=secrets_manager)
        client_for_admin.return_value = client
        keymgr.delete(keyref)
        secrets_manager.delete.assert_called_with(keyref)

    def test_keymgr_get_no_external(self):
        actual_key = 'test_key_super_secret'
        # with no external key manager, get should return the argument
        keyref = keymgr.get(actual_key)
        self.assertEqual(actual_key, keyref)

    @mock.patch('sahara.utils.openstack.barbican.client_for_admin')
    def test_keymgr_get_with_external(self, client_for_admin):
        self.override_config('use_external_key_manager', True)
        actual_key = 'test_key_super_secret'
        keyref = 'test_key_reference'
        secret = mock.Mock(payload=actual_key)
        secrets_manager = mock.Mock()
        secrets_manager.get = mock.Mock(return_value=secret)
        client = mock.Mock(secrets=secrets_manager)
        client_for_admin.return_value = client
        # with external key manager, get should return a key from a reference
        key = keymgr.get(keyref)
        secrets_manager.get.assert_called_with(keyref)
        self.assertEqual(actual_key, key)

    def test_keymgr_store_no_external(self):
        actual_key = 'test_key_super_secret'
        # with no external key manager, store should return the argument
        keyref = keymgr.store(actual_key)
        self.assertEqual(actual_key, keyref)

    @mock.patch('sahara.utils.openstack.barbican.client_for_admin')
    def test_keymgr_store_with_external(self, client_for_admin):
        self.override_config('use_external_key_manager', True)
        key = 'test_key_super_secret'
        actual_keyref = 'test_key_reference'
        secret = mock.Mock()
        secret.store = mock.Mock(return_value=actual_keyref)
        secrets_manager = mock.Mock()
        secrets_manager.create = mock.Mock(return_value=secret)
        client = mock.Mock(secrets=secrets_manager)
        client_for_admin.return_value = client
        # with external key manager, store should return a key reference
        keyref = keymgr.store(key)
        secrets_manager.create.assert_called_with(
            payload=key, payload_content_type='text/plain')
        secret.store.assert_called_once_with()
        self.assertEqual(actual_keyref, keyref)
