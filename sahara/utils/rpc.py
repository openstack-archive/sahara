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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_serialization import jsonutils

from sahara import context
from sahara.i18n import _LI


TRANSPORT = None
NOTIFIER = None

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

_ALIASES = {
    'sahara.openstack.common.rpc.impl_kombu': 'rabbit',
    'sahara.openstack.common.rpc.impl_qpid': 'qpid',
    'sahara.openstack.common.rpc.impl_zmq': 'zmq',
}


class ContextSerializer(messaging.Serializer):
    def __init__(self, base):
        self._base = base

    def serialize_entity(self, ctxt, entity):
        return self._base.serialize_entity(ctxt, entity)

    def deserialize_entity(self, ctxt, entity):
        return self._base.deserialize_entity(ctxt, entity)

    @staticmethod
    def serialize_context(ctxt):
        return ctxt.to_dict()

    @staticmethod
    def deserialize_context(ctxt):
        pass


class JsonPayloadSerializer(messaging.NoOpSerializer):
    @classmethod
    def serialize_entity(cls, context, entity):
        return jsonutils.to_primitive(entity, convert_instances=True)


class RPCClient(object):
    def __init__(self, target):
        global TRANSPORT

        self.__client = messaging.RPCClient(
            target=target,
            transport=TRANSPORT,
        )

    def cast(self, name, **kwargs):
        ctx = context.current()
        self.__client.cast(ctx.to_dict(), name, **kwargs)

    def call(self, name, **kwargs):
        ctx = context.current()
        return self.__client.call(ctx.to_dict(), name, **kwargs)


class RPCServer(object):
    def __init__(self, target):
        global TRANSPORT

        self.__server = messaging.get_rpc_server(
            target=target,
            transport=TRANSPORT,
            endpoints=[self],
            executor='eventlet')

    def get_service(self):
        return self.__server


def setup():
    """Initialise the oslo_messaging layer."""
    global TRANSPORT, NOTIFIER

    messaging.set_transport_defaults('sahara')

    TRANSPORT = messaging.get_transport(cfg.CONF, aliases=_ALIASES)

    if not cfg.CONF.oslo_messaging_notifications.enable:
        LOG.info(_LI("Notifications disabled"))
        return
    LOG.info(_LI("Notifications enabled"))

    serializer = ContextSerializer(JsonPayloadSerializer())
    NOTIFIER = messaging.Notifier(TRANSPORT, serializer=serializer)


def get_notifier(publisher_id):
    """Return a configured oslo_messaging notifier."""
    return NOTIFIER.prepare(publisher_id=publisher_id)
