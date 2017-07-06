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
import functools
import threading

from eventlet import timeout as e_timeout
from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara import conductor
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import base as plugin_base
from sahara.service.health import common
from sahara.utils import cluster as cluster_utils
from sahara.utils.notification import sender

cond = conductor.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class BaseHealthError(ex.SaharaException):
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
    status = common.HEALTH_STATUS_RED


class YellowHealthError(BaseHealthError):
    """Exception to indicate yellow state of health check."""
    code = "YELLOW_STATE"
    status = common.HEALTH_STATUS_YELLOW


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
        timeout = CONF.cluster_verifications.verification_timeout
        try:
            with e_timeout.Timeout(timeout, ex.TimeoutException(timeout)):
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
        except ex.TimeoutException:
            result = _("Health check timed out")
            status = common.HEALTH_STATUS_YELLOW
        self._write_result(status, result)


class AllInstancesAccessible(BasicHealthCheck):
    def __init__(self, cluster, provider):
        self.provider = provider
        super(AllInstancesAccessible, self).__init__(cluster)

    def is_available(self):
        # always available : )
        return True

    def get_health_check_name(self):
        return "Check of instances accessibility"

    def check_health(self):
        inst_ips_or_names = self.provider.get_accessibility_data()
        if inst_ips_or_names:
            insts = ', '.join(inst_ips_or_names)
            LOG.exception(
                "Instances (%s) are not available in the cluster", insts)
            raise RedHealthError(
                _("Instances (%s) are not available in the cluster.") % insts)
        return _("All instances are available")


class ResolvConfIsUnchanged(BasicHealthCheck):
    def __init__(self, cluster, provider):
        self.provider = provider
        super(ResolvConfIsUnchanged, self).__init__(cluster)

    def is_available(self):
        return True

    def get_health_check_name(self):
        return "Check of '/etc/resolv.conf' files"

    def check_health(self):
        bad_inst, bad_res_conf = self.provider.get_resolv_conf_data()
        bad_inst_msg = ''
        res_conf_msg = ''
        if bad_inst:
            insts = ', '.join(bad_inst)
            bad_inst_msg = _("Couldn't read '/etc/resolv.conf' "
                             "on instances: {}.").format(insts)
        if bad_res_conf:
            insts = ', '.join(bad_res_conf)
            ns = ', '.join(CONF.nameservers)
            res_conf_msg = _(
                "Instances ({}) have incorrect '/etc/resolv.conf' "
                "file, expected nameservers: {}.").format(insts, ns)
        if bad_inst_msg or res_conf_msg:
            LOG.exception("{} {}".format(res_conf_msg, bad_inst_msg))
            raise RedHealthError(_("{} {}").format(res_conf_msg, bad_inst_msg))
        return _("All instances have correct '/etc/resolv.conf' file")


class AlertsProvider(object):
    def __init__(self, cluster):
        self._data = None
        self._cluster = cluster
        self._instances = None
        self.get_alerts_data()

    def _instance_get_data(self, instance, lock):
        try:
            with instance.remote() as r:
                data = self._get_resolv_conf(r)
        except Exception:
            data = None
            LOG.exception("Couldn't read '/etc/resolv.conf'")
        with lock:
            self._data[instance.get_ip_or_dns_name()] = data

    def get_accessibility_data(self):
        bad_instances = []
        for el in self._data:
            if self._data[el] is None:
                bad_instances.append(el)
        return bad_instances

    def get_resolv_conf_data(self):
        bad_instances = []
        bad_resolv_conf = []
        for inst_ip_or_name, data in self._data.iteritems():
            if data is None:
                bad_instances.append(inst_ip_or_name)
                continue
            for nameserver in CONF.nameservers:
                if nameserver not in data:
                    bad_resolv_conf.append(inst_ip_or_name)
                    break
        return bad_instances, bad_resolv_conf

    @staticmethod
    def _get_resolv_conf(inst_r):
        # returns None if error occurred while reading resolv.conf
        # otherwise returns content of this file
        code, resolv_conf = inst_r.execute_command(
            "cat /etc/resolv.conf", raise_when_error=False)
        if code != 0:
            return None
        return resolv_conf

    def get_alerts_data(self, check_type=None):
        if check_type and self._data is not None:
            # return cached data
            return self._data.get(check_type, [])
        self._data = {}
        self._instances = cluster_utils.get_instances(self._cluster)
        lock = threading.Lock()
        with context.ThreadGroup() as tg:
            for ins in self._instances:
                tg.spawn('Get health check data of instance %s' % ins.id,
                         self._instance_get_data, ins, lock)
        return self._data


def get_basic(cluster):
    provider = AlertsProvider(cluster)
    basic = [functools.partial(AllInstancesAccessible, provider=provider)]
    if cluster.use_designate_feature():
        basic.append(functools.partial(
            ResolvConfIsUnchanged, provider=provider))
    return basic


def get_health_checks(cluster):
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    plugin_specific = plugin.get_health_checks(cluster)
    plugin_specific.extend(get_basic(cluster))
    return plugin_specific
