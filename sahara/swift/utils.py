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


CONF = cfg.CONF

SWIFT_INTERNAL_PREFIX = "swift://"
# TODO(mattf): remove support for OLD_SWIFT_INTERNAL_PREFIX
OLD_SWIFT_INTERNAL_PREFIX = "swift-internal://"
SWIFT_URL_SUFFIX_START = '.'
SWIFT_URL_SUFFIX = SWIFT_URL_SUFFIX_START + 'sahara'


def retrieve_auth_url():
    """This function returns auth url v2.0 api.

    Hadoop Swift library doesn't support keystone v3 api.
    """
    info = urlparse.urlparse(context.current().auth_uri)

    return "%s://%s:%s/%s/" % (info.scheme, info.hostname, info.port, 'v2.0')
