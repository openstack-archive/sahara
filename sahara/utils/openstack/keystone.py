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
                     'per-job clusters will not be terminated automatically.')
]
CONF.register_opts(opts)


def client():
    ctx = context.current()
    auth_url = base.retrieve_auth_url()

    if CONF.use_identity_api_v3:
        keystone = keystone_client_v3.Client(username=ctx.username,
                                             token=ctx.token,
                                             tenant_id=ctx.tenant_id,
                                             auth_url=auth_url)
        keystone.management_url = auth_url
    else:
        keystone = keystone_client.Client(username=ctx.username,
                                          token=ctx.token,
                                          tenant_id=ctx.tenant_id,
                                          auth_url=auth_url)

    return keystone


def _admin_client(project_name=None, trust_id=None):
    if not CONF.use_identity_api_v3:
        raise Exception('Trusts aren\'t implemented in keystone api'
                        ' less than v3')

    auth_url = base.retrieve_auth_url()
    keystone = keystone_client_v3.Client(username=CONF.os_admin_username,
                                         password=CONF.os_admin_password,
                                         project_name=project_name,
                                         auth_url=auth_url,
                                         trust_id=trust_id)
    keystone.management_url = auth_url
    return keystone


def client_for_admin():
    return _admin_client(project_name=CONF.os_admin_tenant_name)


def client_for_trusts(trust_id):
    return _admin_client(trust_id=trust_id)
