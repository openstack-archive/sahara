# Copyright (c) 2016 Mirantis Inc.
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

import abc

from oslo_log import log as logging
import six

from sahara import conductor
from sahara import context
from sahara import exceptions
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.plugins import base as plugin_base
from sahara.service.health import common
from sahara.utils import cluster as cluster_utils
from sahara.utils.notification import sender

cond = conductor.API
LOG = logging.getLogger(__name__)


class BaseHealthError(exceptions.SaharaException):
    message_template = _("Cluster health is %(status)s. Reason: %(reason)s")
    code = 'HEALTH_ERROR'
    status = 'UNKNOWN'

    def __init__(self, reason):
        message = self.message_template % {
            'status': self.status, 'reason': reason}
        # Ignoring Error id because it's not really needed
        super(BaseHealthError, self).__init__(message, inject_error_id=False)


class RedHealthError(BaseHealthError):
    """Exception to indicate red state of the health check."""
    code = "RED_STATE"
    status = 'RED'


class YellowHealthError(BaseHealthError):
    """Exception to indicate yellow state of health check."""
    code = "YELLOW_STATE"
    status = 'YELLOW'


@six.add_metaclass(abc.ABCMeta)
class BasicHealthCheck(object):
    def __init__(self, cluster):
        """Initialize a health check for the specified cluster."""
        self.cluster = cluster
        self.health_check_id = None

    @abc.abstractmethod
    def get_health_check_name(self):
        """Return name of the health check."""
        pass

    @abc.abstractmethod
    def is_available(self):
        """Validate availability of the health check for the specified cluster

        Return True when the health check is available for the specified
        cluster and False when it's not.
        """
        pass

    @abc.abstractmethod
    def check_health(self):
        """Check health of the specified cluster

        Returns description if health check executed successfully. Raises
        YellowStateError to indicate Yellow result of the health check,
        and RedStateError to indicate Red result of the health check.
        """
        pass

    def _indicate_start(self):
        vid = self.cluster.verification.id
        self.health_check_id = cond.cluster_health_check_add(
            context.ctx(), vid, {'status': common.HEALTH_STATUS_CHECKING,
                                 'name': self.get_health_check_name()}).id
        self.health_check = cond.cluster_health_check_get(
            context.ctx(), self.health_check_id)
        sender.health_notify(self.cluster, self.health_check)

    def _write_result(self, status, description):
        cond.cluster_health_check_update(
            context.ctx(), self.health_check_id,
            {'status': status, 'description': description})
        self.health_check = cond.cluster_health_check_get(
            context.ctx(), self.health_check_id)
        sender.health_notify(self.cluster, self.health_check)

    def execute(self):
        if not self.is_available():
            return
        self._indicate_start()
        try:
            result = self.check_health()
            status = common.HEALTH_STATUS_GREEN
        except Exception as exc:
            result = six.text_type(exc)
            if isinstance(exc, BaseHealthError):
                status = exc.status
            else:
                status = common.HEALTH_STATUS_RED
        self._write_result(status, result)


class AllInstancesAccessible(BasicHealthCheck):
    def __init__(self, cluster):
        super(AllInstancesAccessible, self).__init__(cluster)

    def is_available(self):
        # always available : )
        return True

    def get_health_check_name(self):
        return "Check of instances accessibility"

    @staticmethod
    def _check_health_for_instance(instance):
        with instance.remote() as r:
            r.execute_command("cd /tmp/")

    def check_health(self):
        instances = cluster_utils.get_instances(self.cluster)
        try:
            for inst in instances:
                self._check_health_for_instance(inst)
        except Exception:
            LOG.exception(_LE(
                "Some instances in the cluster are not available"))
            raise RedHealthError(_("Some instances are not available"))

        return _("All instances are available")


def get_basic(cluster):
    return [AllInstancesAccessible]


def get_health_checks(cluster):
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    plugin_specific = plugin.get_health_checks(cluster)
    plugin_specific.extend(get_basic(cluster))
    return plugin_specific
