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


from oslo_config import cfg
import six
from six.moves.urllib import parse as urlparse

from sahara.utils.openstack import base as clients_base


CONF = cfg.CONF

SWIFT_INTERNAL_PREFIX = "swift://"
SWIFT_URL_SUFFIX_START = '.'
SWIFT_URL_SUFFIX = SWIFT_URL_SUFFIX_START + 'sahara'


def retrieve_auth_url(endpoint_type="publicURL"):
    """This function returns auth url v3 api.

    """
    version_suffix = 'v3'

    # return auth url with trailing slash
    return clients_base.retrieve_auth_url(
        endpoint_type=endpoint_type, version=version_suffix) + "/"


def inject_swift_url_suffix(url):
    if isinstance(url, six.string_types) and url.startswith("swift://"):
        u = urlparse.urlparse(url)
        if not u.netloc.endswith(SWIFT_URL_SUFFIX):
            return url.replace(u.netloc,
                               u.netloc + SWIFT_URL_SUFFIX, 1)
    return url
