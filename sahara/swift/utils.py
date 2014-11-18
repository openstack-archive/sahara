# Copyright (c) 2013 Red Hat, Inc.
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
from six.moves.urllib import parse as urlparse

from sahara import context
from sahara.utils.openstack import base as clients_base
from sahara.utils.openstack import keystone as k


CONF = cfg.CONF

SWIFT_INTERNAL_PREFIX = "swift://"
SWIFT_URL_SUFFIX_START = '.'
SWIFT_URL_SUFFIX = SWIFT_URL_SUFFIX_START + 'sahara'


def retrieve_auth_url():
    """This function returns auth url v2.0 api.

    Hadoop Swift library doesn't support keystone v3 api.
    """
    auth_url = clients_base.url_for(context.current().service_catalog,
                                    'identity')
    info = urlparse.urlparse(auth_url)

    if CONF.use_domain_for_proxy_users:
        url = 'v3/auth'
    else:
        url = 'v2.0'

    return '{scheme}://{hostname}:{port}/{url}/'.format(scheme=info.scheme,
                                                        hostname=info.hostname,
                                                        port=info.port,
                                                        url=url)


def retrieve_preauth_url():
    '''This function returns the storage URL for Swift in the current project.

    :returns: The storage URL for the current project's Swift store, or None
              if it can't be found.

    '''
    client = k.client()
    catalog = client.service_catalog.get_endpoints('object-store')
    for ep in catalog.get('object-store'):
        if ep.get('interface') == 'public':
            return ep.get('url')
    return None
