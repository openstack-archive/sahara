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
from eventlet import greenpool
from eventlet import semaphore
from oslo.config import cfg

from sahara import exceptions
from sahara.openstack.common import log as logging


CONF = cfg.CONF
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
                 roles=None,
                 is_admin=None,
                 remote_semaphore=None,
                 **kwargs):
        if kwargs:
            LOG.warn('Arguments dropped when creating context: %s', kwargs)
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.token = token
        self.service_catalog = service_catalog
        self.username = username
        self.tenant_name = tenant_name
        self.is_admin = is_admin
        self.remote_semaphore = remote_semaphore or semaphore.Semaphore(
            CONF.cluster_remote_threshold)
        self.roles = roles

    def clone(self):
        return Context(
            self.user_id,
            self.tenant_id,
            self.token,
            self.service_catalog,
            self.username,
            self.tenant_name,
            self.roles,
            self.is_admin,
            self.remote_semaphore)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'token': self.token,
            'service_catalog': self.service_catalog,
            'username': self.username,
            'tenant_name': self.tenant_name,
            'is_admin': self.is_admin,
            'roles': self.roles,
        }

    def is_auth_capable(self):
        return self.service_catalog and self.token and self.tenant_id and \
            self.user_id


def get_admin_context():
    return Context(is_admin=True)


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


def _wrapper(ctx, thread_description, thread_group, func, *args, **kwargs):
    try:
        set_ctx(ctx)
        func(*args, **kwargs)
    except BaseException as e:
        LOG.exception("Thread '%s' fails with exception: '%s'"
                      % (thread_description, e))
        if thread_group and not thread_group.exc:
            thread_group.exc = e
            thread_group.failed_thread = thread_description
    finally:
        if thread_group:
            thread_group._on_thread_exit()

        set_ctx(None)


def spawn(thread_description, func, *args, **kwargs):
    eventlet.spawn(_wrapper, current().clone(), thread_description,
                   None, func, *args, **kwargs)


class ThreadGroup(object):
    """It is advised to use TreadGroup as a context manager instead
    of instantiating and calling _wait() manually. The __exit__()
    guaranties to exit only after all child threads are done, even if
    spawning code have thrown an exception
    """

    def __init__(self, thread_pool_size=1000):
        self.tg = greenpool.GreenPool(size=thread_pool_size)
        self.exc = None
        self.failed_thread = None
        self.threads = 0
        self.cv = threading.Condition()

    def spawn(self, thread_description, func, *args, **kwargs):
        self.tg.spawn(_wrapper, current().clone(), thread_description,
                      self, func, *args, **kwargs)

        with self.cv:
            self.threads += 1

    def _on_thread_exit(self):
        with self.cv:
            self.threads -= 1
            if self.threads == 0:
                self.cv.notifyAll()

    # NOTE(dmitryme): A little rationale on why we reimplemented wait():
    # * Eventlet's GreenPool.wait() can hung
    # * Oslo's ThreadGroup.wait() can exit before all threads are done
    #
    def _wait(self):
        """It is preferred to use the class as a context manager and do not
        use _wait() directly, see class docstring for an explanation.
        """
        with self.cv:
            while self.threads > 0:
                self.cv.wait()

        if self.exc:
            raise exceptions.ThreadException(self.failed_thread, self.exc)

    def __enter__(self):
        return self

    def __exit__(self, *ex):
        if not any(ex):
            self._wait()
        else:
            # If spawning code thrown an exception, it had higher priority
            # for us than the one thrown inside child thread (if any)
            try:
                self._wait()
            except Exception:
                # that will make __exit__ throw original exception
                pass


def sleep(seconds=0):
    eventlet.sleep(seconds)
