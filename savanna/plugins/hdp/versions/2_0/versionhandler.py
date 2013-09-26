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

from savanna.plugins.hdp.versions import abstractversionhandler as avm


# We have yet to integrate 2.0, so this is essentially a place holder...
class VersionHandler(avm.AbstractVersionHandler):
    version = None

    def _set_version(self, version):
        self.version = version

    def get_version(self):
        return self.version

    def get_config_items(self):
        raise NotImplementedError('not yet supported')

    def get_ambari_client(self):
        raise NotImplementedError('not yet supported')

    def process_node_groups(self, node_groups):
        raise NotImplementedError('not yet supported')

    def get_node_processes(self):
        raise NotImplementedError('not yet supported')

    def process_user_inputs(self, user_inputs):
        raise NotImplementedError('not yet supported')

    def get_applicable_target(self, name):
        raise NotImplementedError('not yet supported')

    def get_cluster_spec(self, cluster, cluster_template):
        raise NotImplementedError('not yet supported')

    def get_default_cluster_configuration(self):
        raise NotImplementedError('not yet supported')

    def process_cluster(self, user_inputs, node_groups):
        raise NotImplementedError('not yet supported')

    def install_swift_integration(self, servers):
        raise NotImplementedError('not yet supported')
