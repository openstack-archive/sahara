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

from sahara.plugins.general import exceptions as ex
from sahara.plugins.general import utils as u
from sahara.plugins.vanilla import utils as vu
from sahara.service.edp.oozie import engine as edp_engine


class EdpOozieEngine(edp_engine.OozieJobEngine):
    def get_hdfs_user(self):
        return 'hadoop'

    def get_name_node_uri(self, cluster):
        return cluster['info']['HDFS']['NameNode']

    def get_oozie_server_uri(self, cluster):
        return cluster['info']['JobFlow']['Oozie'] + "/oozie/"

    def get_oozie_server(self, cluster):
        return vu.get_oozie(cluster)

    def validate_job_execution(self, cluster, job, data):
        oo_count = u.get_instances_count(cluster, 'oozie')
        if oo_count != 1:
            raise ex.InvalidComponentCountException('oozie', '1', oo_count)

        super(EdpOozieEngine, self).validate_job_execution(cluster, job, data)
