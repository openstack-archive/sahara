# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import functools

from sahara.i18n import _
import sahara.plugins.mapr.abstract.health_checker as hc
from sahara.plugins.mapr.domain import node_process as np
from sahara.plugins.mapr.services.management import management
from sahara.plugins.mapr.services.spark import spark
from sahara.service.health import health_check_base


class BaseHealthChecker(hc.AbstractHealthChecker):
    def _is_avaliable(self, process):
        return process.open_ports and process not in spark.SparkOnYarn().\
            node_processes

    def get_checks(self, cluster_context, instances=None):
        checks = [
            functools.partial(ZookeeperCheck, cluster_context=cluster_context)]
        for node_process in cluster_context.get_node_processes():
            if self._is_avaliable(
                    node_process) and node_process.ui_name != 'ZooKeeper':
                checks.append(functools.partial
                              (MapRNodeProcessCheck,
                               cluster_context=cluster_context,
                               process=node_process))
        return checks


class ZookeeperCheck(health_check_base.BasicHealthCheck):
    def __init__(self, cluster, cluster_context):
        super(ZookeeperCheck, self).__init__(cluster)
        self.cluster_context = cluster_context

    def get_health_check_name(self):
        return 'MapR ZooKeeper check'

    def is_available(self):
        return self.cluster_context.cluster.plugin_name == 'mapr'

    def _is_zookeeper_running(self, instance):
        cmd = 'service mapr-zookeeper status'
        with instance.remote() as r:
            __, out = r.execute_command(cmd, run_as_root=True)
            return 'zookeeper running as process' in out

    def check_health(self):
        instances = self.cluster_context.get_instances(
            node_process=management.ZOOKEEPER)
        active_count = 0
        for instance in instances:
            if self._is_zookeeper_running(instance):
                active_count += 1

        if active_count == 0:
            raise health_check_base.RedHealthError(_(
                "ZooKeeper is not in running state"))

        if active_count < len(instances):
            raise health_check_base.YellowHealthError(_(
                "Some ZooKeeper processes are not in running state"))
        return _("ZooKeeper is in running state")


class MapRNodeProcessCheck(health_check_base.BasicHealthCheck):
    IMPORTANT_PROCESSES = [
        'CLDB',
        'FileServer',
        'NodeManager',
        'ResourceManager'
    ]

    def __init__(self, cluster, cluster_context, process):
        super(MapRNodeProcessCheck, self).__init__(cluster)
        self.process = process
        self.cluster_context = cluster_context

    def get_health_check_name(self):
        return 'MapR %s check' % self.process.ui_name

    def is_available(self):
        return self.cluster_context.cluster.plugin_name == 'mapr'

    def check_health(self):
        instances = self.cluster_context.get_instances(
            node_process=self.process)
        active_count = 0
        for instance in instances:
            status = self.process.status(instance)
            if status == np.Status.RUNNING:
                active_count += 1

        if active_count == 0:
            if self.process.ui_name in self.IMPORTANT_PROCESSES:
                raise health_check_base.RedHealthError(_(
                    "%s is not in running state") % self.process.ui_name)
            else:
                raise health_check_base.YellowHealthError(_(
                    "%s is not in running state") % self.process.ui_name)

        if active_count < len(instances):
            if self.process.ui_name in self.IMPORTANT_PROCESSES:
                raise health_check_base.YellowHealthError(_(
                    "Some %s processes are not in running state")
                    % self.process.ui_name)
        return _("%s is in running state") % self.process.ui_name
