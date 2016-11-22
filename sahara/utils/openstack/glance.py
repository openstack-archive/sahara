# Copyright (c) 2016 Mirantis Inc.
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


from glanceclient import client as glance_client
from oslo_config import cfg

from sahara.service import sessions
from sahara.utils.openstack import keystone


opts = [
    cfg.BoolOpt('api_insecure',
                default=False,
                help='Allow to perform insecure SSL requests to glance.'),
    cfg.StrOpt('ca_file',
               help='Location of ca certificates file to use for glance '
                    'client requests.'),
    cfg.StrOpt("endpoint_type",
               default="internalURL",
               help="Endpoint type for glance client requests"),
]

glance_group = cfg.OptGroup(name='glance',
                            title='Glance client options')

CONF = cfg.CONF
CONF.register_group(glance_group)
CONF.register_opts(opts, group=glance_group)


def client():
    session = sessions.cache().get_session(sessions.SESSION_TYPE_GLANCE)
    glance = glance_client.Client('2', session=session, auth=keystone.auth(),
                                  interface=CONF.glance.endpoint_type)
    return glance
