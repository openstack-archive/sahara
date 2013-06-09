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

import threading

from savanna.db import api as db_api
from savanna.openstack.common import log as logging


LOG = logging.getLogger(__name__)


# TODO(slukjanov): it'll be better to use common_context.RequestContext as base
class Context(object):
    def __init__(self, user_id, tenant_id, auth_token, headers, **kwargs):
        if kwargs:
            LOG.warn('Arguments dropped when creating context: %s', kwargs)

        self.user_id = user_id
        self.tenant_id = tenant_id
        self.auth_token = auth_token
        self.headers = headers
        self._db_session = None

    @property
    def session(self):
        if self._db_session is None:
            self._db_session = db_api.get_session()
        return self._db_session


_CTXS = threading.local()


def ctx():
    if not hasattr(_CTXS, '_curr_ctx'):
        # TODO(slukjanov): replace with specific error
        raise RuntimeError("Context isn't available here")
    return _CTXS._curr_ctx


def current():
    return ctx()


def session(context=None):
    context = context or ctx()
    return context.session


def set_ctx(new_ctx):
    if not new_ctx and hasattr(_CTXS, '_curr_ctx'):
        del _CTXS._curr_ctx
    elif new_ctx:
        _CTXS._curr_ctx = new_ctx


def model_query(model, context=None):
    context = context or ctx()
    return context.session.query(model)


def model_save(model, context=None):
    context = context or ctx()
    with context.session.begin():
        context.session.add(model)
    return model
