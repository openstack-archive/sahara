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
import functools

from oslo_config import cfg
import six
import swiftclient

import sahara.exceptions as ex
from sahara.i18n import _
from sahara.service.castellan import utils as key_manager
from sahara.swift import utils as su
from sahara.utils.openstack import swift as sw


CONF = cfg.CONF


def _get_names_from_url(url):
    parse = six.moves.urllib.parse.urlparse(url)
    return (parse.netloc + parse.path).split('/', 1)


def _get_raw_data(job_binary, conn):
    names = _get_names_from_url(job_binary.url)
    container, obj = names

    # if container name has '.sahara' suffix we need to strip it
    if container.endswith(su.SWIFT_URL_SUFFIX):
        container = container[:-len(su.SWIFT_URL_SUFFIX)]

    try:
        # First check the size
        headers = conn.head_object(container, obj)
        total_KB = int(headers.get('content-length', 0)) / 1024.0
        if total_KB > CONF.job_binary_max_KB:
            raise ex.DataTooBigException(
                round(total_KB, 1), CONF.job_binary_max_KB,
                _("Size of swift object (%(size)sKB) is greater "
                  "than maximum (%(maximum)sKB)"))

        headers, body = conn.get_object(container, obj)
    except swiftclient.ClientException as e:
        raise ex.SwiftClientException(six.text_type(e))

    return body


def _validate_job_binary_url(f):
    @functools.wraps(f)
    def wrapper(job_binary, *args, **kwargs):
        if not (job_binary.url.startswith(su.SWIFT_INTERNAL_PREFIX)):
            # This should have been guaranteed already,
            # but we'll check just in case.
            raise ex.BadJobBinaryException(
                _("Url for binary in internal swift must start with %s")
                % su.SWIFT_INTERNAL_PREFIX)
        names = _get_names_from_url(job_binary.url)
        if len(names) == 1:
            # a container has been requested, this is currently unsupported
            raise ex.BadJobBinaryException(
                _('Url for binary in internal swift must specify an object '
                  'not a container'))
        return f(job_binary, *args, **kwargs)
    return wrapper


@_validate_job_binary_url
def get_raw_data(job_binary, proxy_configs=None):
    conn_kwargs = {}
    if proxy_configs:
        conn_kwargs.update(username=proxy_configs.get('proxy_username'),
                           password=key_manager.get_secret(
                           proxy_configs.get('proxy_password')),
                           trust_id=proxy_configs.get('proxy_trust_id'))
    else:
        conn_kwargs.update(username=job_binary.extra.get('user'),
                           password=key_manager.get_secret(
                           job_binary.extra.get('password')))
    conn = sw.client(**conn_kwargs)
    return _get_raw_data(job_binary, conn)


@_validate_job_binary_url
def get_raw_data_with_context(job_binary):
    conn = sw.client_from_token()
    return _get_raw_data(job_binary, conn)
