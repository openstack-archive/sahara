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
from oslo_messaging.rpc import dispatcher
from oslo_serialization import jsonutils

from sahara import context


MESSAGING_TRANSPORT = None
NOTIFICATION_TRANSPORT = None
NOTIFIER = None

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


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
        global MESSAGING_TRANSPORT

        self.__client = messaging.RPCClient(
            target=target,
            transport=MESSAGING_TRANSPORT,
        )

    def cast(self, name, **kwargs):
        ctx = context.current()
        self.__client.cast(ctx.to_dict(), name, **kwargs)

    def call(self, name, **kwargs):
        ctx = context.current()
        return self.__client.call(ctx.to_dict(), name, **kwargs)


class RPCServer(object):
    def __init__(self, target):
        global MESSAGING_TRANSPORT

        access_policy = dispatcher.DefaultRPCAccessPolicy
        self.__server = messaging.get_rpc_server(
            target=target,
            transport=MESSAGING_TRANSPORT,
            endpoints=[self],
            executor='eventlet',
            access_policy=access_policy)

    def get_service(self):
        return self.__server


def setup_service_messaging():
    global MESSAGING_TRANSPORT
    if MESSAGING_TRANSPORT:
        # Already is up
        return
    MESSAGING_TRANSPORT = messaging.get_rpc_transport(cfg.CONF)


def setup_notifications():
    global NOTIFICATION_TRANSPORT, NOTIFIER, MESSAGING_TRANSPORT
    try:
        NOTIFICATION_TRANSPORT = messaging.get_notification_transport(cfg.CONF)
    except Exception:
        LOG.error("Unable to setup notification transport. Reusing "
                  "service transport for that.")
        setup_service_messaging()
        NOTIFICATION_TRANSPORT = MESSAGING_TRANSPORT

    serializer = ContextSerializer(JsonPayloadSerializer())
    NOTIFIER = messaging.Notifier(NOTIFICATION_TRANSPORT,
                                  serializer=serializer)


def setup(service_name):
    """Initialise the oslo_messaging layer."""

    messaging.set_transport_defaults('sahara')
    setup_notifications()
    if service_name != 'all-in-one':
        setup_service_messaging()


def get_notifier(publisher_id):
    """Return a configured oslo_messaging notifier."""
    return NOTIFIER.prepare(publisher_id=publisher_id)
