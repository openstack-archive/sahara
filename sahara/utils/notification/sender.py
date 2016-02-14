# Copyright (c) 2014 Mirantis Inc.
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

from sahara.utils import rpc as messaging

LOG = logging.getLogger(__name__)

SERVICE = 'sahara'
EVENT_TEMPLATE = "sahara.cluster.%s"

notifier_opts = [
    cfg.StrOpt('level',
               default='INFO',
               deprecated_name='notification_level',
               deprecated_group='DEFAULT',
               help='Notification level for outgoing notifications'),
    cfg.StrOpt('publisher_id',
               deprecated_name='notification_publisher_id',
               deprecated_group='DEFAULT',
               help='Notification publisher_id for outgoing notifications'),
    cfg.BoolOpt('enable',
                deprecated_name='enable_notifications',
                deprecated_group='DEFAULT',
                default=False,
                help='Enables sending notifications to Ceilometer')
]

notifier_opts_group = 'oslo_messaging_notifications'

CONF = cfg.CONF
CONF.register_opts(notifier_opts, group=notifier_opts_group)


def _get_publisher():
    publisher_id = CONF.oslo_messaging_notifications.publisher_id
    if publisher_id is None:
        publisher_id = SERVICE
    return publisher_id


def _notify(context, event_type, level, body):
    client = messaging.get_notifier(_get_publisher())

    method = getattr(client, level.lower())
    method(context, event_type, body)


def _body(
        cluster_id,
        cluster_name,
        cluster_status,
        tenant_id,
        user_id):
    result = {
        'cluster_id': cluster_id,
        'cluster_name': cluster_name,
        'cluster_status': cluster_status,
        'project_id': tenant_id,
        'user_id': user_id,
    }
    return result


def notify(context, cluster_id, cluster_name, cluster_status, ev_type):
    """Sends notification about creating/updating/deleting cluster."""
    if not cfg.CONF.oslo_messaging_notifications.enable:
        return

    LOG.debug("Notification about cluster is going to be sent. Notification "
              "type={type}, cluster status = {status}"
              .format(type=ev_type, status=cluster_status))

    level = CONF.oslo_messaging_notifications.level

    _notify(context, EVENT_TEMPLATE % ev_type, level,
            _body(cluster_id, cluster_name, cluster_status, context.tenant_id,
                  context.user_id))
