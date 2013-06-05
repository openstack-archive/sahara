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

from Crypto.PublicKey import RSA
from Crypto import Random
import paramiko
import six


def generate_private_key(length=2048):
    """Generate RSA private key (str) with the specified length."""
    rsa = RSA.generate(length, Random.new().read)
    return rsa.exportKey('PEM')


def to_paramiko_private_key(pkey):
    """Convert private key (str) to paramiko-specific RSAKey object."""
    return paramiko.RSAKey(file_obj=six.StringIO(pkey))


def private_key_to_public_key(key):
    """Convert private key (str) to public key (str)."""
    return RSA.importKey(key).exportKey('OpenSSH')
