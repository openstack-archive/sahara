# Copyright (c) 2013 Mirantis Inc.
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

import unittest2

from savanna.utils import crypto as c


class CryptoTest(unittest2.TestCase):
    def test_generate_private_key(self):
        pk = c.generate_private_key()

        self.assertIsNotNone(pk)
        self.assertIn('-----BEGIN RSA PRIVATE KEY-----', pk)
        self.assertIn('-----END RSA PRIVATE KEY-----', pk)

    def test_to_paramiko_private_key(self):
        pk_str = c.generate_private_key()
        pk = c.to_paramiko_private_key(pk_str)

        self.assertIsNotNone(pk)
        self.assertEqual(2048, pk.size)
        self.assertEqual('ssh-rsa', pk.get_name())

    def test_private_key_to_public_key(self):
        key = c.private_key_to_public_key(c.generate_private_key())

        self.assertIsNotNone(key)
        self.assertIn('ssh-rsa', key)
