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

import re

from keystoneauth1.access import service_catalog as keystone_service_catalog
from keystoneauth1 import exceptions as keystone_ex
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils as json
from six.moves.urllib import parse as urlparse

from sahara import context
from sahara import exceptions as ex

LOG = logging.getLogger(__name__)

# List of the errors, that can be retried
ERRORS_TO_RETRY = [408, 413, 429, 500, 502, 503, 504]

opts = [
    cfg.IntOpt('retries_number',
               default=5,
               help='Number of times to retry the request to client before '
                    'failing'),
    cfg.IntOpt('retry_after',
               default=10,
               help='Time between the retries to client (in seconds).')
]

retries = cfg.OptGroup(name='retries',
                       title='OpenStack clients calls retries')

CONF = cfg.CONF
CONF.register_group(retries)
CONF.register_opts(opts, group=retries)


def url_for(service_catalog=None, service_type='identity',
            endpoint_type="internalURL"):
    if not service_catalog:
        service_catalog = context.current().service_catalog
    try:
        return keystone_service_catalog.ServiceCatalogV2(
            json.loads(service_catalog)).url_for(
                service_type=service_type, interface=endpoint_type,
                region_name=CONF.os_region_name)
    except keystone_ex.EndpointNotFound:
        return keystone_service_catalog.ServiceCatalogV3(
            json.loads(service_catalog)).url_for(
                service_type=service_type, interface=endpoint_type,
                region_name=CONF.os_region_name)


def prepare_auth_url(auth_url, version):
    info = urlparse.urlparse(auth_url)
    url_path = info.path.rstrip("/")
    # replacing current api version to empty string
    url_path = re.sub('/(v3/auth|v3|v2\.0)', '', url_path)
    url_path = (url_path + "/" + version).lstrip("/")
    return "%s://%s/%s" % (info[:2] + (url_path,))


def retrieve_auth_url(endpoint_type="internalURL", version=None):
    if not version:
        version = 'v3' if CONF.use_identity_api_v3 else 'v2.0'
    ctx = context.current()
    if ctx.service_catalog:
        auth_url = url_for(ctx.service_catalog, 'identity', endpoint_type)
    else:
        auth_url = CONF.trustee.auth_url
    return prepare_auth_url(auth_url, version)


def execute_with_retries(method, *args, **kwargs):
    attempts = CONF.retries.retries_number + 1
    while attempts > 0:
        try:
            return method(*args, **kwargs)
        except Exception as e:
            error_code = getattr(e, 'http_status', None) or getattr(
                e, 'status_code', None) or getattr(e, 'code', None)
            if error_code in ERRORS_TO_RETRY:
                LOG.warning('Occasional error occurred during "{method}" '
                            'execution: {error_msg} ({error_code}). '
                            'Operation will be retried.'.format(
                                method=method.__name__,
                                error_msg=e,
                                error_code=error_code))
                attempts -= 1
                retry_after = getattr(e, 'retry_after', 0)
                context.sleep(max(retry_after, CONF.retries.retry_after))
            else:
                LOG.debug('Permanent error occurred during "{method}" '
                          'execution: {error_msg}.'.format(
                              method=method.__name__, error_msg=e))
                raise e
    else:
        attempts = CONF.retries.retries_number
        raise ex.MaxRetriesExceeded(attempts, method.__name__)
