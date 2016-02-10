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

import six

from sahara.i18n import _
from sahara.service.health import health_check_base


@six.add_metaclass(abc.ABCMeta)
class CDHHealthCheck(health_check_base.BasicHealthCheck):
    def get_health_check_name(self):
        return _("CDH cluster health check")

    def is_available(self):
        return (self.cluster.plugin_name == 'cdh' and
                self.cluster.hadoop_version >= '5.4.0')

    @abc.abstractmethod
    def get_cloudera_tools(self):
        # should return correct ClouderaUtils class instance
        pass

    def get_important_services(self):
        # will be overridable in future
        cu = self.get_cloudera_tools()
        return [
            cu.HDFS_SERVICE_NAME,
            cu.YARN_SERVICE_NAME,
            cu.OOZIE_SERVICE_NAME
        ]

    def get_cloudera_health(self):
        cu = self.get_cloudera_tools()
        api = cu.get_api_client(self.cluster)
        return api.get_service_health_status(self.cluster.name)

    def check_health(self):
        important_services = self.get_important_services()
        observed_data = self.get_cloudera_health()
        states = {'green': [], 'yellow': [], 'red': []}
        imp_map = {'BAD': 'red', 'CONCERNING': 'yellow', 'GOOD': 'green'}
        for el in list(observed_data.keys()):
            summary_for_service = observed_data[el]['summary']
            if el in important_services:
                target = imp_map.get(summary_for_service, 'red')
            else:
                target = 'green'
                if summary_for_service != 'GOOD':
                    target = 'yellow'
            states[target].append(el)
        if len(states['red']) > 0:
            raise health_check_base.RedHealthError(
                _("The following services are in red state: %s")
                % states['red'])
        if len(states['yellow']) > 0:
            raise health_check_base.YellowHealthError(
                _("The following services are in yellow state: %s")
                % states['yellow'])
        return _("All services are healthy")
