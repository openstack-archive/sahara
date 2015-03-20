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

    def get_edp_job_types(self):
        return []

    def get_edp_config_hints(self, job_type):
        return {}

    @abc.abstractmethod
    def get_open_ports(self, node_group):
        return

    def on_terminate_cluster(self, cluster):
        pass
