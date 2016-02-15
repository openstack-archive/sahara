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

import collections
import functools

from oslo_log import log as logging
import six

from sahara.i18n import _
from sahara.plugins.ambari import client
from sahara.plugins.ambari import common as p_common
from sahara.plugins import utils as plugin_utils
from sahara.service.health import health_check_base


LOG = logging.getLogger(__name__)


class AlertsProvider(object):
    def __init__(self, cluster):
        self._data = None
        self._cluster_services = None
        self._exception_store = None
        self.cluster = cluster
        # calling to cache all data
        self.get_alerts_data()

    def get_cluster_services(self):
        return self._cluster_services

    def is_ambari_active(self):
        if self._exception_store:
            raise health_check_base.RedHealthError(self._exception_store)
        return _("Ambari Monitor healthy")

    def get_alerts_data(self, service=None):
        if self._data is not None:
            # return cached data
            return self._data.get(service, []) if service else self._data
        self._data = {}
        self._cluster_services = []
        try:
            ambari = plugin_utils.get_instance(
                self.cluster, p_common.AMBARI_SERVER)
            password = self.cluster.extra.get("ambari_password")
            with client.AmbariClient(ambari, password=password) as ambari:
                resp = ambari.get_alerts_data(self.cluster)
            for alert in resp:
                alert = alert.get('Alert', {})
                service = alert.get('service_name').lower()
                if service not in self._data:
                    self._data[service] = []
                    self._cluster_services.append(service)
                self._data[service].append(alert)
        except Exception as e:
            prefix = _("Can't get response from Ambari Monitor")
            msg = _("%(problem)s: %(description)s") % {
                'problem': prefix, 'description': six.text_type(e)}
            # don't put in exception to logs, it will be done by log.exception
            LOG.exception(prefix)
            self._exception_store = msg


class AmbariHealthCheck(health_check_base.BasicHealthCheck):
    def __init__(self, cluster, provider):
        self.provider = provider
        super(AmbariHealthCheck, self).__init__(cluster)

    def get_health_check_name(self):
        return "Ambari alerts health check"

    def is_available(self):
        return self.cluster.plugin_name == 'ambari'

    def check_health(self):
        return self.provider.is_ambari_active()


class AmbariServiceHealthCheck(health_check_base.BasicHealthCheck):
    def __init__(self, cluster, provider, service):
        self.provider = provider
        self.service = service.lower()
        super(AmbariServiceHealthCheck, self).__init__(cluster)

    def get_health_check_name(self):
        return "Ambari alerts for %s Service" % self.service

    def is_available(self):
        return self.cluster.plugin_name == 'ambari'

    def get_important_services(self):
        return [
            p_common.HDFS_SERVICE.lower(),
            p_common.YARN_SERVICE.lower(),
            p_common.OOZIE_SERVICE.lower(),
            p_common.ZOOKEEPER_SERVICE.lower()
        ]

    def check_health(self):
        imp_map = {'OK': 'GREEN', 'WARNING': 'YELLOW', 'CRITICAL': 'RED'}
        other_map = {'OK': 'GREEN'}
        color_counter = collections.Counter()
        important_services = self.get_important_services()
        for alert in self.provider.get_alerts_data(self.service):
            alert_summary = alert.get('state', 'UNKNOWN')
            if self.service in important_services:
                target = imp_map.get(alert_summary, 'RED')
            else:
                target = other_map.get(alert_summary, 'YELLOW')
            color_counter[target] += 1
        if color_counter['RED'] > 0 and color_counter['YELLOW'] > 0:
            raise health_check_base.RedHealthError(
                _("Ambari Monitor has responded that cluster has "
                  "%(red)d critical and %(yellow)d warning alert(s)")
                % {'red': color_counter['RED'],
                   'yellow': color_counter['YELLOW']})
        elif color_counter['RED'] > 0:
            raise health_check_base.RedHealthError(
                _("Ambari Monitor has responded that cluster has "
                  "%(red)d critical alert(s)")
                % {'red': color_counter['RED']})
        elif color_counter['YELLOW'] > 0:
            raise health_check_base.YellowHealthError(
                _("Ambari Monitor has responded that cluster "
                  "has %d warning alert(s)")
                % color_counter['YELLOW'])
        return _("No alerts found")


def get_health_checks(cluster):
    provider = AlertsProvider(cluster)
    checks = [functools.partial(AmbariHealthCheck, provider=provider)]
    for service in provider.get_cluster_services():
        checks.append(functools.partial(
            AmbariServiceHealthCheck, provider=provider, service=service))
    return checks
