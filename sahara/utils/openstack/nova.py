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

from novaclient import client as nova_client
from oslo_config import cfg

from sahara.service import sessions
import sahara.utils.openstack.base as base
from sahara.utils.openstack import keystone


opts = [
    cfg.BoolOpt('api_insecure',
                default=False,
                help='Allow to perform insecure SSL requests to nova.'),
    cfg.StrOpt('ca_file',
               help='Location of ca certificates file to use for nova '
                    'client requests.'),
    cfg.StrOpt("endpoint_type",
               default="internalURL",
               help="Endpoint type for nova client requests")
]

nova_group = cfg.OptGroup(name='nova',
                          title='Nova client options')

CONF = cfg.CONF
CONF.register_group(nova_group)
CONF.register_opts(opts, group=nova_group)


def client():
    session = sessions.cache().get_session(sessions.SESSION_TYPE_NOVA)
    nova = nova_client.Client('2', session=session, auth=keystone.auth(),
                              endpoint_type=CONF.nova.endpoint_type,
                              region_name=CONF.os_region_name)
    return nova


def get_flavor(**kwargs):
    return base.execute_with_retries(client().flavors.find, **kwargs)


def get_instance_info(instance):
    return base.execute_with_retries(
        client().servers.get, instance.instance_id)


def get_keypair(keypair_name):
    return base.execute_with_retries(
        client().keypairs.get, keypair_name)
