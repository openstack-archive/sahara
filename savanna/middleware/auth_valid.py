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

from webob.exc import HTTPServiceUnavailable, HTTPNotFound, HTTPUnauthorized

from savanna.openstack.commons import split_path
from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class AuthValidator:
    """
    Auth Validation Middleware handles token auth results and tenants
    """

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf

    def __call__(self, env, start_response):
        """
        Handle incoming request by checking tenant info prom the headers and
        url ({tenant_id} url attribute).

        Pass request downstream on success.
        Reject request if tenant_id from headers not equals to tenant_id from
        url.
        """
        token_tenant = env['HTTP_X_TENANT_ID']
        if not token_tenant:
            LOG.warn("Can't get tenant_id from env")
            resp = HTTPServiceUnavailable()
            return resp(env, start_response)

        path = env['PATH_INFO']
        version, url_tenant, rest = split_path(path, 3, 3, True)

        if not version or not url_tenant or not rest:
            LOG.info("Incorrect path: %s", path)
            resp = HTTPNotFound("Incorrect path")
            resp(env, start_response)

        if token_tenant != url_tenant:
            LOG.debug("Unauthorized: token tenant != requested tenant")
            resp = HTTPUnauthorized('Token tenant != requested tenant')
            return resp(env, start_response)

        return self.app(env, start_response)


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return AuthValidator(app, conf)

    return auth_filter
