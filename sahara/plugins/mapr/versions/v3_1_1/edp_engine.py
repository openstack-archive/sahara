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


import sahara.plugins.mapr.base.base_edp_engine as edp
import sahara.plugins.mapr.util.maprfs_helper as mfs


class MapR3OozieJobEngine(edp.MapROozieJobEngine):
    def create_hdfs_dir(self, remote, dir_name):
        mfs.create_maprfs3_dir(remote, dir_name, self.get_hdfs_user())
