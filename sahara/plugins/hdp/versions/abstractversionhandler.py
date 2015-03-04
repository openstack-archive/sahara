# Copyright (c) 2013 Hortonworks, Inc.
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
    def get_config_items(self):
        return

    @abc.abstractmethod
    def get_applicable_target(self, name):
        return

    @abc.abstractmethod
    def get_cluster_spec(self, cluster, user_inputs, scaled_groups=None,
                         cluster_template=None):
        return

    @abc.abstractmethod
    def get_ambari_client(self):
        return

    @abc.abstractmethod
    def get_default_cluster_configuration(self):
        return

    @abc.abstractmethod
    def get_node_processes(self):
        return

    @abc.abstractmethod
    def install_swift_integration(self, servers):
        return

    @abc.abstractmethod
    def get_version(self):
        return

    @abc.abstractmethod
    def get_services_processor(self):
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
        return []
