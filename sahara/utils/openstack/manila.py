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

import manilaclient.client as manila_client
try:
    from manilaclient.common.apiclient import exceptions as manila_ex
except ImportError:
    from manilaclient.openstack.common.apiclient import exceptions as manila_ex
from oslo_config import cfg

from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.utils.openstack import base


opts = [
    cfg.StrOpt('api_version', default='1',
               help='Version of the manila API to use.'),
    cfg.BoolOpt('api_insecure',
                default=True,
                help='Allow to perform insecure SSL requests to manila.'),
    cfg.StrOpt('ca_file',
               help='Location of ca certificates file to use for manila '
                    'client requests.')
]

manila_group = cfg.OptGroup(name='manila',
                            title='Manila client options')

CONF = cfg.CONF
CONF.register_group(manila_group)
CONF.register_opts(opts, group=manila_group)

MANILA_PREFIX = "manila://"


def client():
    ctx = context.ctx()
    args = {
        'username': ctx.username,
        'project_name': ctx.tenant_name,
        'project_id': ctx.tenant_id,
        'input_auth_token': context.get_auth_token(),
        'auth_url': base.retrieve_auth_url(),
        'service_catalog_url': base.url_for(ctx.service_catalog, 'share'),
        'ca_cert': CONF.manila.ca_file,
        'insecure': CONF.manila.api_insecure
    }
    return manila_client.Client(CONF.manila.api_version, **args)


def get_share(client_instance, share_id, raise_on_error=False):
    try:
        return client_instance.shares.get(share_id)
    except manila_ex.NotFound:
        if raise_on_error:
            raise ex.NotFoundException(
                share_id, _("Share with id %s was not found."))
        else:
            return None
