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


import abc

import six


@six.add_metaclass(abc.ABCMeta)
class AbstractVersionHandler(object):
    @abc.abstractmethod
    def get_node_processes(self):
        return

    @abc.abstractmethod
    def get_configs(self):
        return

    @abc.abstractmethod
    def configure_cluster(self, cluster):
        pass

    @abc.abstractmethod
    def start_cluster(self, cluster):
        pass

    @abc.abstractmethod
    def validate(self, cluster):
        pass

    @abc.abstractmethod
    def validate_scaling(self, cluster, existing, additional):
        pass

    @abc.abstractmethod
    def scale_cluster(self, cluster, instances):
        pass

    @abc.abstractmethod
    def decommission_nodes(self, cluster, instances):
        pass

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
    def get_context(self, cluster, added=None, removed=None):
        return

    @abc.abstractmethod
    def get_services(self):
        return

    @abc.abstractmethod
    def get_required_services(self):
        return

    @abc.abstractmethod
    def get_open_ports(self, node_group):
        return
