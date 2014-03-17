# Copyright (c) 2013 Intel Corporation
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

from sahara import context
from sahara.openstack.common import log as logging
from sahara.plugins.intel import exceptions as iex


LOG = logging.getLogger(__name__)


def get(ctx, session_id):
    url = '/cluster/%s/session/%s' % (ctx.cluster_name, session_id)
    return ctx.rest.get(url)


def wait(ctx, session_id):
    #TODO(alazarev) add check on Hadoop cluster state (exit on delete)
    #TODO(alazarev) make configurable (bug #1262897)
    timeout = 4*60*60  # 4 hours
    cur_time = 0
    while cur_time < timeout:
        info_items = get(ctx, session_id)['items']
        for item in info_items:
            progress = item['nodeprogress']
            if progress['info'].strip() == '_ALLFINISH':
                return
            else:
                context.sleep(10)
                cur_time += 10

            debug_msg = 'Hostname: %s\nInfo: %s'
            debug_msg = debug_msg % (progress['hostname'], progress['info'])
            LOG.debug(debug_msg)
    else:
        raise iex.IntelPluginException(
            "Cluster '%s' has failed to start in %s minutes"
            % (ctx.cluster_name, timeout / 60))
