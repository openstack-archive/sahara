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

import functools

from oslo_log import log as logging
import six

from sahara.i18n import _
from sahara.service.health import health_check_base

LOG = logging.getLogger(__name__)


class HealthStatusProvider(object):
    def __init__(self, cluster, cloudera_tools):
        self.cluster = cluster
        self.cloudera_tools = cloudera_tools
        self._data = None
        self._cluster_services = None
        self._exception_store = None
        self.get_health_status()

    def get_cluster_services(self):
        return self._cluster_services

    def is_cloudera_active(self):
        if self._exception_store:
            raise health_check_base.RedHealthError(self._exception_store)
        return _("Cloudera Manager is Active")

    def get_cloudera_health(self):
        cu = self.cloudera_tools
        api = cu.get_api_client(self.cluster)
        return api.get_service_health_status(self.cluster.name)

    def get_important_services(self):
        # will be overridable in future
        cu = self.cloudera_tools
        return [
            cu.HDFS_SERVICE_NAME,
            cu.YARN_SERVICE_NAME,
            cu.OOZIE_SERVICE_NAME
        ]

    def get_health_status(self, service=None):
        if self._data is not None:
            return self._data.get(service, []) if service else self._data
        self._data = {}
        self._cluster_services = []
        try:
            # all data already grouped by services
            self._data = self.get_cloudera_health()
            self._cluster_services = self._data.keys()
        except Exception as e:
            msg = _("Can't get response from Cloudera "
                    "Manager")
            LOG.exception(msg)
            self._exception_store = _(
                "%(problem)s, reason: %(reason)s") % {
                'problem': msg, 'reason': six.text_type(e)}


class ClouderaManagerHealthCheck(health_check_base.BasicHealthCheck):
    def __init__(self, cluster, provider):
        self.provider = provider
        super(ClouderaManagerHealthCheck, self).__init__(cluster)

    def get_health_check_name(self):
        return _("Cloudera Manager health check")

    def is_available(self):
        return (self.cluster.plugin_name == 'cdh' and
                self.cluster.hadoop_version >= '5.4.0')

    def check_health(self):
        return self.provider.is_cloudera_active()


class ServiceHealthCheck(health_check_base.BasicHealthCheck):
    def __init__(self, cluster, provider, service):
        self.provider = provider
        self.service = service
        super(ServiceHealthCheck, self).__init__(cluster)

    def get_health_check_name(self):
        return _("CDH %s health check") % self.service

    def is_available(self):
        return (self.cluster.plugin_name == 'cdh' and
                self.cluster.hadoop_version >= '5.4.0')

    def check_health(self):
        important_services = self.provider.get_important_services()
        observed_data = self.provider.get_health_status(self.service)
        imp_map = {'BAD': 'red', 'CONCERNING': 'yellow', 'GOOD': 'green'}
        summary = observed_data['summary']
        checks = observed_data.get('checks', [])
        failed_checks = []
        for check in checks:
            if check['summary'] != 'GOOD':
                failed_checks.append('%(name)s - %(summary)s state' % {
                    'name': check['name'], 'summary': check['summary']
                })
        additional_info = None
        if failed_checks:
            additional_info = _(
                "The following checks did not pass: %s") % ",".join(
                failed_checks)
        if self.service in important_services:
            overall = imp_map.get(summary, 'red')
        else:
            overall = 'green'
            if summary != 'GOOD':
                overall = 'yellow'
        msg = _("Cloudera Manager has responded that service is in "
                "the %s state") % summary
        if additional_info:
            msg = _("%(problem)s. %(description)s") % {
                'problem': msg, 'description': additional_info}
        if overall == 'red':
            raise health_check_base.RedHealthError(msg)
        elif overall == 'yellow':
            raise health_check_base.YellowHealthError(msg)
        return msg


def get_health_checks(cluster, cloudera_utils):
    provider = HealthStatusProvider(cluster, cloudera_utils)
    checks = [functools.partial(
        ClouderaManagerHealthCheck, provider=provider)]
    for service in provider.get_cluster_services():
        checks.append(functools.partial(
            ServiceHealthCheck, provider=provider, service=service))
    return checks
