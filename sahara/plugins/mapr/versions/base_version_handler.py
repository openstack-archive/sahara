# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import abc

import six

import sahara.plugins.mapr.util.plugin_spec as ps
import sahara.plugins.mapr.util.start_helper as sh
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.plugins.mapr.versions.edp_engine as edp


@six.add_metaclass(abc.ABCMeta)
class BaseVersionHandler(object):

    def __init__(self):
        self.plugin_spec = ps.PluginSpec(self.get_plugin_spec_path())

    def get_plugin_spec(self):
        return self.plugin_spec

    def get_configs(self):
        return self.plugin_spec.get_configs()

    def get_node_processes(self):
        return self.plugin_spec.service_node_process_map

    def get_disk_setup_script(self):
        return 'plugins/mapr/util/resources/create_disk_list_file.sh'

    def validate(self, cluster):
        rules = self.get_cluster_validation_rules(cluster)
        for rule in rules:
            rule(cluster)

    def validate_scaling(self, cluster, existing, additional):
        fake_cluster = vu.create_fake_cluster(cluster, existing, additional)
        self.validate(fake_cluster)

    def validate_edp(self, cluster):
        for rule in self.get_edp_validation_rules():
            rule(cluster)

    def configure_cluster(self, cluster):
        sh.install_roles(cluster, self.get_context(cluster))
        self.get_cluster_configurer(cluster, self.plugin_spec).configure()

    def get_name_node_uri(self, cluster):
        return self.get_context(cluster).get_cldb_uri()

    def get_oozie_server(self, cluster):
        return self.get_context(cluster).get_oozie_instance()

    def get_oozie_server_uri(self, cluster):
        return self.get_context(cluster).get_oozie_uri()

    def get_resource_manager_uri(self, cluster):
        return self.get_context(cluster).get_rm_uri()

    def get_home_dir(self):
        return ('plugins/mapr/versions/v%s'
                % self.get_plugin_version().replace('.', '_').lower())

    def get_plugin_spec_path(self):
        return '%s/resources/plugin_spec.json' % self.get_home_dir()

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp.MapROozieJobEngine.get_supported_job_types():
            return edp.MapROozieJobEngine(cluster)
        return None

    # Astract methods

    @abc.abstractmethod
    def get_plugin_version(self):
        return

    @abc.abstractmethod
    def get_cluster_validation_rules(self, cluster):
        return

    @abc.abstractmethod
    def get_scaling_validation_rules(self):
        return

    def get_waiting_script(self):
        return

    @abc.abstractmethod
    def get_edp_validation_rules(self):
        return

    @abc.abstractmethod
    def get_cluster_configurer(self, cluster, plugin_spec):
        return

    @abc.abstractmethod
    def get_configure_sh_string(self, cluster):
        return

    @abc.abstractmethod
    def get_context(self, cluster):
        return
