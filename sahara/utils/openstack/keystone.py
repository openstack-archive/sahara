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

from keystoneclient.v2_0 import client as keystone_client
from keystoneclient.v3 import client as keystone_client_v3
from oslo.config import cfg

from sahara import context
from sahara.utils.openstack import base


CONF = cfg.CONF

opts = [
    cfg.BoolOpt('use_identity_api_v3',
                default=True,
                help='Enables Sahara to use Keystone API v3. '
                     'If that flag is disabled, '
                     'per-job clusters will not be terminated '
                     'automatically.')
]
CONF.register_opts(opts)


def client():
    '''Return the current context client.'''
    ctx = context.current()

    return _client(username=ctx.username, token=ctx.token,
                   tenant_id=ctx.tenant_id)


def _client(username, password=None, token=None, tenant_name=None,
            tenant_id=None, trust_id=None, domain_name=None):

    if trust_id and not CONF.use_identity_api_v3:
        raise Exception("Trusts aren't implemented in keystone api"
                        " less than v3")

    auth_url = base.retrieve_auth_url()

    client_kwargs = {'username': username,
                     'password': password,
                     'token': token,
                     'tenant_name': tenant_name,
                     'tenant_id': tenant_id,
                     'trust_id': trust_id,
                     'user_domain_name': domain_name,
                     'auth_url': auth_url}

    if CONF.use_identity_api_v3:
        keystone = keystone_client_v3.Client(**client_kwargs)
        keystone.management_url = auth_url
    else:
        keystone = keystone_client.Client(**client_kwargs)

    return keystone


def _admin_client(project_name=None, trust_id=None):
    username = CONF.keystone_authtoken.admin_user
    password = CONF.keystone_authtoken.admin_password
    keystone = _client(username=username,
                       password=password,
                       tenant_name=project_name,
                       trust_id=trust_id)
    return keystone


def client_for_admin():
    '''Return the Sahara admin user client.'''
    return _admin_client(
        project_name=CONF.keystone_authtoken.admin_tenant_name)


def client_for_admin_from_trust(trust_id):
    '''Return the Sahara admin user client scoped to a trust.'''
    return _admin_client(trust_id=trust_id)


def client_for_proxy_user(username, password, trust_id=None):
    '''Return a client for the proxy user specified.'''
    return _client(username=username,
                   password=password,
                   domain_name=CONF.proxy_user_domain_name,
                   trust_id=trust_id)
