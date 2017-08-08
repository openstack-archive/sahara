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
from castellan.key_manager import key_manager as km


"""sahara.service.castellan.sahara_key_manager

This module contains the KeyManager class that will be used by the
castellan library, it is not meant for direct usage within sahara.
"""


class SaharaKeyManager(km.KeyManager):
    """Sahara specific key manager

    This manager is a thin wrapper around the secret being stored. It is
    intended for backward compatible use only. It will not store keys
    or generate UUIDs but instead return the secret that is being stored.
    This behavior allows Sahara to continue storing secrets in its database
    while using the Castellan key manager abstraction.
    """
    def __init__(self, configuration=None):
        pass

    def create_key(self, context, algorithm=None, length=0,
                   expiration=None, **kwargs):
        """creates a key

        algorithm, length, and expiration are unused by sahara keys.
        """
        return key.Passphrase(passphrase=kwargs.get('passphrase', ''))

    def create_key_pair(self, *args, **kwargs):
        pass

    def store(self, context, key, expiration=None, **kwargs):
        """store a key

        in normal usage a store_key will return the UUID of the key as
        dictated by the key manager. Sahara would then store this UUID in
        its database to use for retrieval. As sahara is not actually using
        a key manager in this context it will return the key's payload for
        storage.
        """
        return key.get_encoded()

    def get(self, context, key_id, **kwargs):
        """get a key

        since sahara is not actually storing key UUIDs the key_id to this
        function should actually be the key payload. this function will
        simply return a new SaharaKey based on that value.
        """
        return key.Passphrase(passphrase=key_id)

    def delete(self, context, key_id, **kwargs):
        """delete a key

        as there is no external key manager, this function will not
        perform any external actions. therefore, it won't change anything.
        """
        pass

    def list(self, *args, **kwargs):
        """list all managed keys

        current implementation of the key manager does not utilize this
        """
        pass
