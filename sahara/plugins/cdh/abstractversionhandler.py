# Copyright (c) 2014 Mirantis, Inc.
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

from sahara import conductor
from sahara import context
from sahara.plugins.cdh import db_helper as dh
from sahara.plugins.cdh import health


@six.add_metaclass(abc.ABCMeta)
class AbstractVersionHandler(object):

    @abc.abstractmethod
    def get_node_processes(self):
        return

    @abc.abstractmethod
    def get_plugin_configs(self):
        return

    @abc.abstractmethod
    def configure_cluster(self, cluster):
        return

    @abc.abstractmethod
    def start_cluster(self, cluster):
        return

    @abc.abstractmethod
    def validate(self, cluster):
        return

    @abc.abstractmethod
    def scale_cluster(self, cluster, instances):
        return

    @abc.abstractmethod
    def decommission_nodes(self, cluster, instances):
        return

    @abc.abstractmethod
    def validate_scaling(self, cluster, existing, additional):
        return

    @abc.abstractmethod
    def get_edp_engine(self, cluster, job_type):
        return

    @abc.abstractmethod
    def get_edp_job_types(self):
        return []

    @abc.abstractmethod
    def get_edp_config_hints(self, job_type):
        return {}

    @abc.abstractmethod
    def get_open_ports(self, node_group):
        return

    def on_terminate_cluster(self, cluster):
        dh.delete_passwords_from_keymanager(cluster)


class BaseVersionHandler(AbstractVersionHandler):

    def __init__(self):
        # Need to be specitied in subclass
        self.config_helper = None  # config helper
        self.cloudera_utils = None  # CoulderaUtils
        self.deploy = None  # to deploy
        self.edp_engine = None
        self.plugin_utils = None  # PluginUtils
        self.validation = None  # to validate

    def get_plugin_configs(self):
        return self.config_helper.get_plugin_configs()

    def get_node_processes(self):
        raise NotImplementedError()

    def validate(self, cluster):
        self.validation.validate_cluster_creating(cluster)

    def configure_cluster(self, cluster):
        self.deploy.configure_cluster(cluster)
        conductor.API.cluster_update(
            context.ctx(), cluster, {
                'info':
                self.cloudera_utils.get_cloudera_manager_info(cluster)})

    def start_cluster(self, cluster):
        self.deploy.start_cluster(cluster)

        self._set_cluster_info(cluster)

    def decommission_nodes(self, cluster, instances):
        self.deploy.decommission_cluster(cluster, instances)

    def validate_scaling(self, cluster, existing, additional):
        self.validation.validate_existing_ng_scaling(cluster, existing)
        self.validation.validate_additional_ng_scaling(cluster, additional)

    def scale_cluster(self, cluster, instances):
        self.deploy.scale_cluster(cluster, instances)

    def _set_cluster_info(self, cluster):
        info = self.cloudera_utils.get_cloudera_manager_info(cluster)
        hue = self.cloudera_utils.pu.get_hue(cluster)
        if hue:
            info['Hue Dashboard'] = {
                'Web UI': 'http://%s:8888' % hue.get_ip_or_dns_name()
            }

        ctx = context.ctx()
        conductor.API.cluster_update(ctx, cluster, {'info': info})

    def get_edp_engine(self, cluster, job_type):
        oozie_type = self.edp_engine.EdpOozieEngine.get_supported_job_types()
        if job_type in oozie_type:
            return self.edp_engine.EdpOozieEngine(cluster)
        return None

    def get_edp_job_types(self):
        return self.edp_engine.EdpOozieEngine.get_supported_job_types()

    def get_edp_config_hints(self, job_type):
        return self.edp_engine.EdpOozieEngine.get_possible_job_config(job_type)

    def get_open_ports(self, node_group):
        return self.deploy.get_open_ports(node_group)

    def recommend_configs(self, cluster, scaling):
        self.plugin_utils.recommend_configs(
            cluster, self.get_plugin_configs(), scaling)

    def get_health_checks(self, cluster):
        return health.get_health_checks(cluster, self.cloudera_utils)
