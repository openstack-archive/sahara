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

from heatclient import client as heat_client
from oslo_config import cfg

from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.utils.openstack import base


opts = [
    cfg.BoolOpt('api_insecure',
                default=False,
                help='Allow to perform insecure SSL requests to heat.'),
    cfg.StrOpt('ca_file',
               help='Location of ca certificates file to use for heat '
                    'client requests.'),
    cfg.StrOpt("endpoint_type",
               default="internalURL",
               help="Endpoint type for heat client requests")
]

heat_group = cfg.OptGroup(name='heat',
                          title='Heat client options')

CONF = cfg.CONF
CONF.register_group(heat_group)
CONF.register_opts(opts, group=heat_group)


def client():
    ctx = context.current()
    heat_url = base.url_for(ctx.service_catalog, 'orchestration',
                            endpoint_type=CONF.heat.endpoint_type)
    return heat_client.Client('1', heat_url, token=ctx.auth_token,
                              cert_file=CONF.heat.ca_file,
                              insecure=CONF.heat.api_insecure,
                              username=ctx.username,
                              include_pass=True)


def get_stack(stack_name, raise_on_missing=True):
    for stack in base.execute_with_retries(
            client().stacks.list, show_hidden=True,
            filters={'name': stack_name}):
        return stack

    if not raise_on_missing:
        return None

    raise ex.NotFoundException({'stack': stack_name},
                               _('Failed to find stack %(stack)s'))


def _verify_completion(stack, is_update=False, last_update_time=None):
    # NOTE: expected empty status because status of stack
    # maybe is not set in heat database
    if stack.status in ['IN_PROGRESS', '']:
        return False
    if is_update and stack.status == 'COMPLETE':
        if stack.updated_time == last_update_time:
            return False
    return True


def wait_stack_completion(stack, is_update=False, last_updated_time=None):
    base.execute_with_retries(stack.get)
    while not _verify_completion(stack, is_update, last_updated_time):
        context.sleep(1)
        base.execute_with_retries(stack.get)

    if stack.status != 'COMPLETE':
        raise ex.HeatStackException(stack.stack_status)


def get_resource(stack, resource):
    return base.execute_with_retries(
        client().resources.get, stack, resource)
