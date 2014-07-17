# Copyright (c) 2014 Mirantis Inc.
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

from sahara.i18n import _
from sahara.plugins import provisioning as p


class FakePluginProvider(p.ProvisioningPluginBase):

    def get_title(self):
        return "Fake Plugin"

    def get_description(self):
        return _("It's a fake plugin that aimed to work on the CirrOS images. "
                 "It doesn't install Hadoop. It's needed to be able to test "
                 "provisioning part of Sahara codebase itself.")

    def get_versions(self):
        return ["0.1"]

    def get_node_processes(self, hadoop_version):
        return {
            "HDFS": ["namenode", "datanode"],
            "MapReduce": ["tasktracker", "jobtracker"],
        }

    def get_configs(self, hadoop_version):
        # no need to expose any configs, it could be checked using real plugins
        return []

    def configure_cluster(self, cluster):
        # noop
        pass

    def start_cluster(self, cluster):
        # noop
        pass
