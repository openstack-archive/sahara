# Copyright (c) 2014 Red Hat, Inc.
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

from oslo.config import cfg

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.utils.openstack import keystone as k


PROXY_DOMAIN = None
CONF = cfg.CONF

opts = [
    cfg.BoolOpt('use_domain_for_proxy_users',
                default=False,
                help='Enables Sahara to use a domain for creating temporary '
                     'proxy users to access Swift. If this is enabled '
                     'a domain must be created for Sahara to use.'),
    cfg.StrOpt('proxy_user_domain_name',
               default=None,
               help='The domain Sahara will use to create new proxy users '
                    'for Swift object access.')
]
CONF.register_opts(opts)


def domain_for_proxy():
    '''Return the proxy domain or None

    If configured to use the proxy domain, this function will return that
    domain. If not configured to use the proxy domain, this function will
    return None. If the proxy domain can't be found this will raise an
    exception.

    :returns: A Keystone Domain object or None.
    :raises ConfigurationError: If the domain is requested but not specified.
    :raises NotFoundException: If the domain name is specified but cannot be
                               found.

    '''
    if CONF.use_domain_for_proxy_users is False:
        return None
    if CONF.proxy_user_domain_name is None:
        raise ex.ConfigurationError(_('Proxy domain requested but not '
                                      'specified.'))
    admin = k.client_for_admin()

    global PROXY_DOMAIN
    if not PROXY_DOMAIN:
        domain_list = admin.domains.list(name=CONF.proxy_user_domain_name)
        if len(domain_list) == 0:
            raise ex.NotFoundException(value=CONF.proxy_user_domain_name,
                                       message=_('Failed to find domain %s'))
        # the domain name should be globally unique in Keystone
        if len(domain_list) > 1:
            raise ex.NotFoundException(value=CONF.proxy_user_domain_name,
                                       message=_('Unexpected results found '
                                                 'when searching for domain '
                                                 '%s'))
        PROXY_DOMAIN = domain_list[0]
    return PROXY_DOMAIN
