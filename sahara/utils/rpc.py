# Copyright (c) 2013 Mirantis Inc.
# Copyright (c) 2013 Julien Danjou <julien@danjou.info>
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
from oslo import messaging

from sahara import context
from sahara.i18n import _LE
from sahara.openstack.common import log as logging


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class RPCClient(object):
    def __init__(self, target):
        self.__client = messaging.RPCClient(
            target=target,
            transport=messaging.get_transport(cfg.CONF),
        )

    def cast(self, name, **kwargs):
        ctx = context.current()
        self.__client.cast(ctx.to_dict(), name, **kwargs)

    def call(self, name, **kwargs):
        ctx = context.current()
        return self.__client.call(ctx.to_dict(), name, **kwargs)


class RPCServer(object):
    def __init__(self, target):
        self.__server = messaging.get_rpc_server(
            target=target,
            transport=messaging.get_transport(cfg.CONF),
            endpoints=[ContextEndpointHandler(self)],
            executor='eventlet'
        )

    def start(self):
        self.__server.start()
        self.__server.wait()


class ContextEndpointHandler(object):
    def __init__(self, endpoint):
        self.__endpoint = endpoint

    def __getattr__(self, name):
        try:
            method = getattr(self.__endpoint, name)

            def run_method(ctx, **kwargs):
                context.set_ctx(context.Context(**ctx))
                try:
                    return method(**kwargs)
                finally:
                    context.set_ctx(None)

            return run_method
        except AttributeError:
            LOG.error(_LE("No %(method)s method found implemented in "
                      "%(class)s class"),
                      {'method': name, 'class': self.__endpoint})
