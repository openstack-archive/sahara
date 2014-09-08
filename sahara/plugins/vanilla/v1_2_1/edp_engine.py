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

from sahara.plugins.vanilla import edp_engine
from sahara.service.edp import hdfs_helper


class EdpOozieEngine(edp_engine.EdpOozieEngine):

    def create_hdfs_dir(self, remote, dir_name):
        hdfs_helper.create_dir_hadoop1(remote, dir_name, self.get_hdfs_user())

    def get_resource_manager_uri(self, cluster):
        return cluster['info']['MapReduce']['JobTracker']
