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

from castellan.common.objects import passphrase as key

from sahara.service.castellan import sahara_key_manager
from sahara.tests.unit import base


class SaharaKeyManagerTest(base.SaharaTestCase):

    def setUp(self):
        super(SaharaKeyManagerTest, self).setUp()
        self.k_m = sahara_key_manager.SaharaKeyManager()
        self.ctx = None

    def test_create_key(self):
        k = self.k_m.create_key(self.ctx, passphrase='super_secret')
        self.assertEqual('super_secret', k.get_encoded())

        k = self.k_m.create_key(self.ctx)
        self.assertEqual('', k.get_encoded())

    def test_store(self):
        k = key.Passphrase(passphrase='super_secret')
        k_id = self.k_m.store(self.ctx, k)
        self.assertEqual('super_secret', k_id)

    def test_get(self):
        k_id = 'super_secret'
        k = self.k_m.get(self.ctx, k_id)
        self.assertEqual(k_id, k.get_encoded())
