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

import eventlet
from eventlet import corolocal

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

    def clone(self):
        return Context(self.user_id,
                       self.tenant_id,
                       self.auth_token,
                       self.headers)

    @property
    def session(self):
        if self._db_session is None:
            self._db_session = db_api.get_session()
        return self._db_session


_CTXS = threading.local()
_CTXS._curr_ctxs = {}


def has_ctx():
    ident = corolocal.get_ident()
    return ident in _CTXS._curr_ctxs and _CTXS._curr_ctxs[ident]


def ctx():
    if not has_ctx():
        # TODO(slukjanov): replace with specific error
        raise RuntimeError("Context isn't available here")
    return _CTXS._curr_ctxs[corolocal.get_ident()]


def current():
    return ctx()


def session(context=None):
    context = context or ctx()
    return context.session


def set_ctx(new_ctx):
    ident = corolocal.get_ident()

    if not new_ctx and ident in _CTXS._curr_ctxs:
        del _CTXS._curr_ctxs[ident]

    if new_ctx:
        _CTXS._curr_ctxs[ident] = new_ctx


def model_query(model, context=None, project_only=None):
    context = context or ctx()
    query = context.session.query(model)

    if project_only:
        query = query.filter_by(tenant_id=context.tenant_id)

    return query


def model_save(model, context=None):
    context = context or ctx()
    with context.session.begin():
        context.session.add(model)
    return model


def model_update(model, context=None, **kwargs):
    if not hasattr(model, '__table__'):
        # TODO(slikjanov): replace with specific exception
        raise RuntimeError("Specified object isn't model, class: %s"
                           % model.__class__.__name__)
    columns = model.__table__.columns
    for prop in kwargs:
        if prop not in columns:
            # TODO(slukjanov): replace with specific exception
            raise RuntimeError(
                "Model class '%s' doesn't contains specified property '%s'"
                % (model.__class__.__name__, prop))
        setattr(model, prop, kwargs[prop])

    return model_save(model, context)


def spawn(func, *args, **kwargs):
    ctx = current().clone()

    def wrapper(ctx, func, *args, **kwargs):
        set_ctx(ctx)
        func(*args, **kwargs)

    eventlet.spawn(wrapper, ctx, func, *args, **kwargs)


def sleep(seconds=0):
    eventlet.sleep(seconds)
