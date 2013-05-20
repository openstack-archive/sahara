# Copyright (c) 2013 Mirantis Inc.
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

from savanna.plugins.provisioning import Config
from savanna.plugins.provisioning import ProvisioningPluginBase


class VanillaProvider(ProvisioningPluginBase):
    def get_plugin_opts(self):
        return []

    def setup(self, conf):
        self.conf = conf

    def get_title(self):
        return "Vanilla Apache Hadoop"

    def get_description(self):
        return (
            "This plugin provides an ability to launch vanilla Apache Hadoop "
            "cluster without any management consoles.")

    def get_versions(self):
        return ['Hadoop 1.1.1']

    def get_configs(self, ctx, hadoop_version):
        return [
            Config('heap_size', 'tasktracker', default_value='1024M')
        ]

    def get_node_processes(self, ctx, hadoop_version):
        return [
            'jobtracker', 'tasktracker',
            'namenode', 'datanode',
        ]

    def validate(self, ctx, cluster):
        pass

    def update_infra(self, ctx, cluster):
        pass

    def configure_cluster(self, ctx, cluster):
        pass

    def start_cluster(self, ctx, cluster):
        pass
