# Copyright (c) 2016 Red Hat, Inc.
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

from castellan.common.objects import passphrase
from castellan import key_manager

from sahara import context


def delete_secret(id, ctx=None):
    """delete a secret from the external key manager

    :param id: The identifier of the secret to delete
    :param ctx: The context, and associated authentication, to use with
                this operation (defaults to the current context)
    """
    if ctx is None:
        ctx = context.current()
    key_manager.API().delete(ctx, id)


def get_secret(id, ctx=None):
    """get a secret associated with an id

    :param id: The identifier of the secret to retrieve
    :param ctx: The context, and associated authentication, to use with
                this operation (defaults to the current context)
    """
    if ctx is None:
        ctx = context.current()
    key = key_manager.API().get(ctx, id)
    return key.get_encoded()


def store_secret(secret, ctx=None):
    """store a secret and return its identifier

    :param secret: The secret to store, this should be a string
    :param ctx: The context, and associated authentication, to use with
                this operation (defaults to the current context)
    """
    if ctx is None:
        ctx = context.current()
    key = passphrase.Passphrase(secret)
    return key_manager.API().store(ctx, key)
