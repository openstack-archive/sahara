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

from savanna.openstack.common import log as logging


LOG = logging.getLogger(__name__)


# TODO(slukjanov): it'll be better to use common_context.RequestContext as base
class Context(object):
    def __init__(self,
                 user_id=None,
                 tenant_id=None,
                 token=None,
                 service_catalog=None,
                 username=None,
                 tenant_name=None,
                 **kwargs):
        if kwargs:
            LOG.warn('Arguments dropped when creating context: %s', kwargs)
        self.user_id = user_id
        self.username = username
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.token = token
        self.service_catalog = service_catalog
        self._db_session = None

    def clone(self):
        return Context(
            self.user_id,
            self.tenant_id,
            self.token,
            self.service_catalog,
            self.username,
            self.tenant_name)


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


def set_ctx(new_ctx):
    ident = corolocal.get_ident()

    if not new_ctx and ident in _CTXS._curr_ctxs:
        del _CTXS._curr_ctxs[ident]

    if new_ctx:
        _CTXS._curr_ctxs[ident] = new_ctx


def spawn(thread_description, func, *args, **kwargs):
    ctx = current().clone()

    def wrapper(ctx, func, *args, **kwargs):
        try:
            set_ctx(ctx)
            func(*args, **kwargs)
            set_ctx(None)
        except Exception as e:
            LOG.exception("Thread '%s' fails with exception: '%s'"
                          % (thread_description, e))

    eventlet.spawn(wrapper, ctx, func, *args, **kwargs)


def sleep(seconds=0):
    eventlet.sleep(seconds)
