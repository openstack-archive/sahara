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

from sahara.i18n import _LI
from sahara.openstack.common import log as logging
import sahara.plugins.mapr.versions.base_cluster_configurer as bcc
import sahara.plugins.utils as u
from sahara.utils import files as f

LOG = logging.getLogger(__name__)


class ClusterConfigurer(bcc.BaseClusterConfigurer):
    hadoop_version_path = '/opt/mapr/conf/hadoop_version'
    hadoop_mode = 'classic'
    hadoop_version_local = 'plugins/mapr/util/resources/hadoop_version'

    def get_hadoop_conf_dir(self):
        return '/opt/mapr/hadoop/hadoop-0.20.2/conf'

    def is_node_awareness_enabled(self):
        return True

    def set_cluster_mode(self, instances):
        if not instances:
            instances = u.get_instances(self.cluster)
        LOG.info(_LI('Setting cluster mode to classic'))
        hv_template = f.get_file_text(self.hadoop_version_local)
        hv = hv_template % {"mode": self.hadoop_mode}
        for i in instances:
            with i.remote() as r:
                LOG.debug('Writing file %(f_name)s to node %(node)s',
                          {'f_name': self.hadoop_version_path,
                           'node': i.management_ip})
                r.write_file_to(self.hadoop_version_path, hv,
                                run_as_root=True)

    def configure_instances(self, instances=None):
        super(ClusterConfigurer, self).configure_instances(instances)
        self.set_cluster_mode(instances)
