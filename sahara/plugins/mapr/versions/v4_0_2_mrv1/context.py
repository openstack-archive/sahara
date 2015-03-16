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


class Context(bc.BaseClusterContext):
    def __init__(self, cluster, version_handler, added=None, removed=None):
        super(Context, self).__init__(cluster, version_handler, added, removed)
        self._hadoop_version = mr.MapReduce().version
        self._hadoop_lib = None
        self._hadoop_conf = None
        self._resource_manager_uri = 'maprfs:///'
        self._cluster_mode = mr.MapReduce.cluster_mode
        self._node_aware = True
        self._mapr_version = '4.0.2'
        self._ubuntu_ecosystem_repo = (
            'http://package.mapr.com/releases/ecosystem-4.x/ubuntu binary/')
        self._centos_ecosystem_repo = (
            'http://package.mapr.com/releases/ecosystem-4.x/redhat')

    @property
    def hadoop_lib(self):
        if not self._hadoop_lib:
            self._hadoop_lib = '%s/lib' % self.hadoop_home
        return self._hadoop_lib

    @property
    def hadoop_conf(self):
        if not self._hadoop_conf:
            self._hadoop_conf = '%s/conf' % self.hadoop_home
        return self._hadoop_conf

    @property
    def resource_manager_uri(self):
        return self._resource_manager_uri
