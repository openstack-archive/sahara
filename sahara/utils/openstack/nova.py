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

from novaclient import exceptions as nova_ex
from novaclient.v2 import client as nova_client
from oslo_config import cfg

from sahara import context
import sahara.utils.openstack.base as base
from sahara.utils.openstack import images


opts = [
    cfg.BoolOpt('api_insecure',
                default=False,
                help='Allow to perform insecure SSL requests to nova.'),
    cfg.StrOpt('ca_file',
               help='Location of ca certificates file to use for nova '
                    'client requests.')
]

nova_group = cfg.OptGroup(name='nova',
                          title='Nova client options')

CONF = cfg.CONF
CONF.register_group(nova_group)
CONF.register_opts(opts, group=nova_group)


def client():
    ctx = context.current()
    auth_url = base.retrieve_auth_url()
    compute_url = base.url_for(ctx.service_catalog, 'compute')

    nova = nova_client.Client(username=ctx.username,
                              api_key=None,
                              project_id=ctx.tenant_id,
                              auth_url=auth_url,
                              cacert=CONF.nova.ca_file,
                              insecure=CONF.nova.api_insecure)

    nova.client.auth_token = ctx.auth_token
    nova.client.management_url = compute_url
    nova.images = images.SaharaImageManager(nova)
    return nova


def get_flavors():
    return [flavor.name for flavor in client().flavors.list()]


def get_flavor(**kwargs):
    return client().flavors.find(**kwargs)


def get_images():
    return [image.id for image in client().images.list()]


def get_limits():
    limits = client().limits.get().absolute
    return dict((l.name, l.value) for l in limits)


def get_user_keypair(cluster):
    try:
        return client().keypairs.get(cluster.user_keypair_id)
    except nova_ex.NotFound:
        return None


def get_instance_info(instance):
    return client().servers.get(instance.instance_id)


def get_network(**kwargs):
    try:
        return client().networks.find(**kwargs)
    except nova_ex.NotFound:
        return None
