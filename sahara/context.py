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

import eventlet
from eventlet.green import threading
from eventlet.green import time
from eventlet import greenpool
from eventlet import semaphore
from oslo_config import cfg
from oslo_context import context
from oslo_log import log as logging

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LW


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class Context(context.RequestContext):
    def __init__(self,
                 user_id=None,
                 tenant_id=None,
                 auth_token=None,
                 service_catalog=None,
                 username=None,
                 tenant_name=None,
                 roles=None,
                 is_admin=None,
                 remote_semaphore=None,
                 auth_uri=None,
                 resource_uuid=None,
                 current_instance_info=None,
                 overwrite=True,
                 **kwargs):
        if kwargs:
            LOG.warning(_LW('Arguments dropped when creating context: '
                            '{args}').format(args=kwargs))

        super(Context, self).__init__(auth_token=auth_token,
                                      user=user_id,
                                      tenant=tenant_id,
                                      is_admin=is_admin,
                                      resource_uuid=resource_uuid)
        self.service_catalog = service_catalog
        self.username = username
        self.tenant_name = tenant_name
        self.remote_semaphore = remote_semaphore or semaphore.Semaphore(
            CONF.cluster_remote_threshold)
        self.roles = roles
        if auth_uri:
            self.auth_uri = auth_uri
        else:
            self.auth_uri = _get_auth_uri()
        if overwrite or not hasattr(context._request_store, 'context'):
            self.update_store()

        if current_instance_info is not None:
            self.current_instance_info = current_instance_info
        else:
            self.current_instance_info = InstanceInfo()

    def clone(self):
        return Context(
            self.user_id,
            self.tenant_id,
            self.auth_token,
            self.service_catalog,
            self.username,
            self.tenant_name,
            self.roles,
            self.is_admin,
            self.remote_semaphore,
            self.auth_uri,
            self.resource_uuid,
            self.current_instance_info,
            overwrite=False)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'auth_token': self.auth_token,
            'service_catalog': self.service_catalog,
            'username': self.username,
            'tenant_name': self.tenant_name,
            'is_admin': self.is_admin,
            'roles': self.roles,
            'auth_uri': self.auth_uri,
            'resource_uuid': self.resource_uuid,
        }

    def is_auth_capable(self):
        return (self.service_catalog and self.auth_token and self.tenant and
                self.user_id)

    # NOTE(adrienverge): The Context class uses the 'user' and 'tenant'
    # properties internally (inherited from oslo.context), but Sahara code
    # often uses 'user_id' and 'tenant_id'.
    @property
    def user_id(self):
        return self.user

    @user_id.setter
    def user_id(self, value):
        self.user = value

    @property
    def tenant_id(self):
        return self.tenant

    @tenant_id.setter
    def tenant_id(self, value):
        self.tenant = value


def get_admin_context():
    return Context(is_admin=True)


_CTX_STORE = threading.local()
_CTX_KEY = 'current_ctx'


def has_ctx():
    return hasattr(_CTX_STORE, _CTX_KEY)


def ctx():
    if not has_ctx():
        raise ex.IncorrectStateError(_("Context isn't available here"))
    return getattr(_CTX_STORE, _CTX_KEY)


def current():
    return ctx()


def set_ctx(new_ctx):
    if not new_ctx and has_ctx():
        delattr(_CTX_STORE, _CTX_KEY)
        if hasattr(context._request_store, 'context'):
            delattr(context._request_store, 'context')

    if new_ctx:
        setattr(_CTX_STORE, _CTX_KEY, new_ctx)
        setattr(context._request_store, 'context', new_ctx)


def _get_auth_uri():
    if CONF.keystone_authtoken.auth_uri is not None:
        auth_uri = CONF.keystone_authtoken.auth_uri
    else:
        if CONF.keystone_authtoken.identity_uri is not None:
            identity_uri = CONF.keystone_authtoken.identity_uri
        else:
            host = CONF.keystone_authtoken.auth_host
            port = CONF.keystone_authtoken.auth_port
            protocol = CONF.keystone_authtoken.auth_protocol
            identity_uri = '%s://%s:%s' % (protocol, host, port)

        if CONF.use_identity_api_v3 is False:
            auth_version = 'v2.0'
        else:
            auth_version = 'v3'

        auth_uri = '%s/%s' % (identity_uri, auth_version)

    return auth_uri


def _wrapper(ctx, thread_description, thread_group, func, *args, **kwargs):
    try:
        set_ctx(ctx)
        func(*args, **kwargs)
    except BaseException as e:
        LOG.debug(
            "Thread {thread} failed with exception: {exception}".format(
                thread=thread_description, exception=e))
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
    """ThreadGroup object.

    It is advised to use TreadGroup as a context manager instead
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
        """Using of _wait() method.

        It is preferred to use the class as a context manager and do not
        use _wait() directly, see class docstring for an explanation.
        """
        with self.cv:
            while self.threads > 0:
                self.cv.wait()

        if self.exc:
            raise ex.ThreadException(self.failed_thread, self.exc)

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
    time.sleep(seconds)


class InstanceInfo(object):
    def __init__(self, cluster_id=None, instance_id=None, instance_name=None,
                 node_group_id=None):
        self.cluster_id = cluster_id
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.node_group_id = node_group_id


class InstanceInfoManager(object):
    def __init__(self, instance_info):
        self.prev_instance_info = current().current_instance_info
        current().current_instance_info = instance_info

    def __enter__(self):
        pass

    def __exit__(self, *args):
        current().current_instance_info = self.prev_instance_info
