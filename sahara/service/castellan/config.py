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

from castellan import options as castellan
from oslo_config import cfg

from sahara.utils.openstack import base as utils


opts = [
    cfg.BoolOpt('use_barbican_key_manager', default=False,
                help='Enable the usage of the OpenStack Key Management '
                     'service provided by barbican.'),
]

castellan_opts = [
    cfg.StrOpt('barbican_api_endpoint',
               help='The endpoint to use for connecting to the barbican '
                    'api controller. By default, castellan will use the '
                    'URL from the service catalog.'),
    cfg.StrOpt('barbican_api_version', default='v1',
               help='Version of the barbican API, for example: "v1"'),
]

castellan_group = cfg.OptGroup(name='castellan',
                               title='castellan key manager options')

CONF = cfg.CONF
CONF.register_group(castellan_group)
CONF.register_opts(opts)
CONF.register_opts(castellan_opts, group=castellan_group)


def validate_config():
    if CONF.use_barbican_key_manager:
        # NOTE (elmiko) there is no need to set the api_class as castellan
        # uses barbican by default.
        castellan.set_defaults(CONF, auth_endpoint=utils.retrieve_auth_url())
    else:
        castellan.set_defaults(CONF, api_class='sahara.service.castellan.'
                               'sahara_key_manager.SaharaKeyManager')
