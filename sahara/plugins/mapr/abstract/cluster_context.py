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
class AbstractClusterContext(object):
    @abc.abstractproperty
    def mapr_home(self):
        return

    @abc.abstractproperty
    def configure_sh_path(self):
        return

    @abc.abstractproperty
    def configure_sh(self):
        return

    @abc.abstractproperty
    def hadoop_version(self):
        return

    @abc.abstractproperty
    def hadoop_home(self):
        return

    @abc.abstractproperty
    def hadoop_lib(self):
        return

    @abc.abstractproperty
    def hadoop_conf(self):
        return

    @abc.abstractproperty
    def cluster(self):
        return

    @abc.abstractproperty
    def name_node_uri(self):
        return

    @abc.abstractproperty
    def resource_manager_uri(self):
        return

    @abc.abstractproperty
    def oozie_server_uri(self):
        return

    @abc.abstractproperty
    def oozie_server(self):
        return

    @abc.abstractproperty
    def oozie_http(self):
        return

    @abc.abstractproperty
    def cluster_mode(self):
        return

    @abc.abstractproperty
    def is_node_aware(self):
        return

    @abc.abstractproperty
    def some_instance(self):
        return

    @abc.abstractproperty
    def distro(self):
        return

    @abc.abstractproperty
    def mapr_db(self):
        return

    @abc.abstractmethod
    def filter_instances(self, instances, node_process=None, service=None):
        return

    @abc.abstractmethod
    def removed_instances(self, node_process=None, service=None):
        return

    @abc.abstractmethod
    def added_instances(self, node_process=None, service=None):
        return

    @abc.abstractmethod
    def changed_instances(self, node_process=None, service=None):
        return

    @abc.abstractmethod
    def existing_instances(self, node_process=None, service=None):
        return

    @abc.abstractproperty
    def should_be_restarted(self):
        return

    @abc.abstractproperty
    def mapr_repos(self):
        return

    @abc.abstractproperty
    def is_prebuilt(self):
        return

    @abc.abstractproperty
    def local_repo(self):
        return

    @abc.abstractproperty
    def required_services(self):
        return

    @abc.abstractproperty
    def all_services(self):
        return

    @abc.abstractproperty
    def mapr_version(self):
        return

    @abc.abstractproperty
    def ubuntu_base_repo(self):
        return

    @abc.abstractproperty
    def ubuntu_ecosystem_repo(self):
        return

    @abc.abstractproperty
    def centos_base_repo(self):
        return

    @abc.abstractproperty
    def centos_ecosystem_repo(self):
        return
