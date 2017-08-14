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

from sahara import context
from sahara.utils import rpc as messaging

LOG = logging.getLogger(__name__)

SERVICE = 'sahara'
CLUSTER_EVENT_TEMPLATE = "sahara.cluster.%s"
HEALTH_EVENT_TYPE = CLUSTER_EVENT_TEMPLATE % "health"

notifier_opts = [
    cfg.StrOpt('level',
               default='INFO',
               deprecated_name='notification_level',
               deprecated_group='DEFAULT',
               help='Notification level for outgoing notifications'),
    cfg.StrOpt('publisher_id',
               deprecated_name='notification_publisher_id',
               deprecated_group='DEFAULT',
               help='Identifier of the publisher')
]

notifier_opts_group = 'oslo_messaging_notifications'

CONF = cfg.CONF
CONF.register_opts(notifier_opts, group=notifier_opts_group)


def _get_publisher():
    publisher_id = CONF.oslo_messaging_notifications.publisher_id
    if publisher_id is None:
        publisher_id = SERVICE
    return publisher_id


def _notify(event_type, body):
    LOG.debug("Notification about cluster is going to be sent. Notification "
              "type={type}".format(type=event_type))
    ctx = context.ctx()
    level = CONF.oslo_messaging_notifications.level

    body.update({'project_id': ctx.tenant_id, 'user_id': ctx.user_id})
    client = messaging.get_notifier(_get_publisher())

    method = getattr(client, level.lower())
    method(ctx, event_type, body)


def _health_notification_body(cluster, health_check):
    verification = cluster.verification
    return {
        'cluster_id': cluster.id,
        'cluster_name': cluster.name,
        'verification_id': verification['id'],
        'health_check_status': health_check['status'],
        'health_check_name': health_check['name'],
        'health_check_description': health_check['description'],
        'created_at': health_check['created_at'],
        'updated_at': health_check['updated_at']
    }


def status_notify(cluster_id, cluster_name, cluster_status, ev_type):
    """Sends notification about creating/updating/deleting cluster."""
    _notify(CLUSTER_EVENT_TEMPLATE % ev_type, {
        'cluster_id': cluster_id, 'cluster_name': cluster_name,
        'cluster_status': cluster_status})


def health_notify(cluster, health_check):
    """Sends notification about current cluster health."""
    _notify(HEALTH_EVENT_TYPE,
            _health_notification_body(cluster, health_check))
