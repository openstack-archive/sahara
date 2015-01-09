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


import sahara.plugins.mapr.base.base_cluster_context as bc
import sahara.plugins.mapr.services.mapreduce.mapreduce as mr
from sahara.utils import files as f


class Context(bc.BaseClusterContext):
    UBUNTU_MAPR_BASE_REPO = ('http://package.mapr.com/releases/v4.0.1/ubuntu/ '
                             'mapr optional')
    UBUNTU_MAPR_ECOSYSTEM_REPO = ('http://package.mapr.com/releases/'
                                  'ecosystem-4.x/ubuntu binary/')
    CENTOS_MAPR_BASE_REPO = 'http://package.mapr.com/releases/v4.0.1/redhat/'
    CENTOS_MAPR_ECOSYSTEM_REPO = ('http://package.mapr.com/releases/'
                                  'ecosystem-4.x/redhat')

    def __init__(self, cluster, version_handler, added=None, removed=None):
        super(Context, self).__init__(cluster, version_handler, added, removed)
        self._hadoop_version = mr.MapReduce().version
        self._hadoop_lib = None
        self._hadoop_conf = None
        self._resource_manager_uri = 'maprfs:///'
        self._cluster_mode = mr.MapReduce.cluster_mode
        self._node_aware = False

    @property
    def hadoop_lib(self):
        if not self._hadoop_lib:
            f = '%(hadoop_home)s/lib'
            args = {
                'hadoop_home': self.hadoop_home,
            }
            self._hadoop_lib = f % args
        return self._hadoop_lib

    @property
    def hadoop_conf(self):
        if not self._hadoop_conf:
            f = '%(hadoop_home)s/conf'
            args = {
                'hadoop_home': self.hadoop_home,
            }
            self._hadoop_conf = f % args
        return self._hadoop_conf

    @property
    def resource_manager_uri(self):
        return self._resource_manager_uri

    def get_install_repo_script_data(self):
        script_template = 'plugins/mapr/resources/add_mapr_repo.sh'
        script_template = f.get_file_text(script_template)
        args = {
            "ubuntu_mapr_base_repo": Context.UBUNTU_MAPR_BASE_REPO,
            "ubuntu_mapr_ecosystem_repo": Context.UBUNTU_MAPR_ECOSYSTEM_REPO,
            "centos_mapr_repo": Context.CENTOS_MAPR_BASE_REPO,
            "centos_mapr_ecosystem_repo": Context.CENTOS_MAPR_ECOSYSTEM_REPO,
        }
        return script_template % args
