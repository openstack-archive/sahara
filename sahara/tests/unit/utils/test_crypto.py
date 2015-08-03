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

import testtools

from sahara.utils import crypto as c


class CryptoTest(testtools.TestCase):
    def test_generate_key_pair(self):
        kp = c.generate_key_pair()

        self.assertIsInstance(kp, tuple)
        self.assertIsNotNone(kp[0])
        self.assertIsNotNone(kp[1])
        self.assertIn('-----BEGIN RSA PRIVATE KEY-----', kp[0])
        self.assertIn('-----END RSA PRIVATE KEY-----', kp[0])
        self.assertIn('ssh-rsa ', kp[1])
        self.assertIn('Generated-by-Sahara', kp[1])

    def test_to_paramiko_private_key(self):
        pk_str = c.generate_key_pair()[0]
        pk = c.to_paramiko_private_key(pk_str)

        self.assertIsNotNone(pk)
        self.assertEqual(2048, pk.size)
        self.assertEqual('ssh-rsa', pk.get_name())
