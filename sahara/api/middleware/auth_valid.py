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

from oslo_log import log as logging
from oslo_middleware import base
from oslo_utils import strutils
from oslo_utils import uuidutils
import webob
import webob.exc as ex

from sahara.i18n import _


LOG = logging.getLogger(__name__)


class AuthValidator(base.Middleware):

    """Handles token auth results and tenants."""

    @webob.dec.wsgify
    def __call__(self, req):
        """Ensures that tenants in url and token are equal.

        Handle incoming request by checking tenant info prom the headers and
        url ({tenant_id} url attribute).

        Pass request downstream on success.
        Reject request if tenant_id from headers not equals to tenant_id from
        url.
        """
        token_tenant = req.environ.get("HTTP_X_TENANT_ID")
        if not token_tenant:
            LOG.warning("Can't get tenant_id from env")
            raise ex.HTTPServiceUnavailable()

        path = req.environ['PATH_INFO']
        if path != '/':
            try:
                version, possibly_url_tenant, rest = (
                    strutils.split_path(path, 2, 3, True)
                )
            except ValueError:
                LOG.warning("Incorrect path: {path}".format(path=path))
                raise ex.HTTPNotFound(_("Incorrect path"))

            if uuidutils.is_uuid_like(possibly_url_tenant):
                url_tenant = possibly_url_tenant
                if token_tenant != url_tenant:
                    LOG.debug("Unauthorized: token tenant != requested tenant")
                    raise ex.HTTPUnauthorized(
                        _('Token tenant != requested tenant'))
        return self.application
