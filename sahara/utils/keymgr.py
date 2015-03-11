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

from oslo_config import cfg
from oslo_log import log as logging

from sahara.utils.openstack import barbican


LOG = logging.getLogger(__name__)
CONF = cfg.CONF

opts = [
    cfg.BoolOpt('use_external_key_manager',
                default=False,
                help='Enable Sahara to use an external key manager service '
                     'provided by the identity service catalog. Sahara will '
                     'store all keys with the manager service.')
]
CONF.register_opts(opts)


def delete(key_ref):
    '''delete a key

    When this function is used without an external key manager it does
    nothing to the provided reference.

    :param key_ref: The reference of the key to delete

    '''
    if CONF.use_external_key_manager:
        client = barbican.client_for_admin()
        client.secrets.delete(key_ref)
        LOG.debug('Deleted key {key_ref}'.format(key_ref=key_ref))
    else:
        LOG.debug('External key manager not enabled, key not deleted')


def get(key_ref):
    '''retrieve a key

    When used with an external key manager this will retrieve the key
    and return it as stored.

    When used without an external key manager it will return the argument
    provided.

    :param key_ref: The reference of the key to retrieve
    :returns: The retrieved key

    '''
    if CONF.use_external_key_manager:
        client = barbican.client_for_admin()
        key = client.secrets.get(key_ref)
        LOG.debug('Retrieved key for {key_ref}'.format(key_ref=key_ref))
        payload = key.payload
        return payload
    else:
        return key_ref


def store(key):
    '''store a key

    When used with an external key manager this function will store the key
    in the manager and return a reference provided by the manager.

    When used without an external manager this function will return the
    argument provided.

    :param key: The key to store
    :returns: A reference for the stored key

    '''
    if CONF.use_external_key_manager:
        client = barbican.client_for_admin()
        secret = client.secrets.create(payload=key,
                                       payload_content_type='text/plain')
        secret_ref = secret.store()
        LOG.debug('Stored key as {key_ref}'.format(key_ref=secret_ref))
        return secret_ref
    else:
        return key
