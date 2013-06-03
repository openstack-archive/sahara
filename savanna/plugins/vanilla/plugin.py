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

from savanna.openstack.common import log as logging
from savanna.plugins import provisioning as p
from savanna.plugins.vanilla import config_helper as c_helper
from savanna.plugins.vanilla import exceptions as ex
from savanna.plugins.vanilla import utils

LOG = logging.getLogger(__name__)


class VanillaProvider(p.ProvisioningPluginBase):
    def __init__(self):
        self.processes = {
            "HDFS": ["namenode", "datanode", "secondarynamenode"],
            "MAPREDUCE": ["tasktracker", "jobtracker"]
        }

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
        return ['1.1.2']

    def get_configs(self, hadoop_version):
        return c_helper.get_plugin_configs()

    def get_node_processes(self, hadoop_version):
        return self.processes

    def validate(self, cluster):
        nn_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "namenode")])
        if nn_count is not 1:
            raise ex.NotSingleNameNodeException(nn_count)

        jt_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "jobtracker")])

        if jt_count not in [0, 1]:
            raise ex.NotSingleJobTrackerException(jt_count)

        tt_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "tasktracker")])
        if jt_count is 0 and tt_count > 0:
            raise ex.TaskTrackersWithoutJobTracker()

    def update_infra(self, cluster):
        pass

    def configure_cluster(self, cluster):
        for ng in cluster.node_groups:
            for inst in ng.instances:
                inst.remote.execute_command(
                    'sudo chown -R $USER:$USER /etc/hadoop'
                )

        self._extract_configs(cluster)
        self._push_configs_to_nodes(cluster)

    def start_cluster(self, cluster):
        nn_instance = utils.get_namenode(cluster)
        jt_instance = utils.get_jobtracker(cluster)

        nn_instance.remote.execute_command(
            'sudo su -c /usr/sbin/start-dfs.sh hadoop >>'
            ' /tmp/savanna-hadoop-start-dfs.log')

        LOG.info("HDFS service at '%s' has been started", nn_instance.hostname)

        if jt_instance:
            jt_instance.remote.execute_command(
                'sudo su -c /usr/sbin/start-mapred.sh hadoop >>'
                ' /tmp/savanna-hadoop-start-mapred.log')
            LOG.info("MAPREDUCE service at '%s' has been started",
                     jt_instance.hostname)

        LOG.info('Cluster %s has been started successfully' % cluster.name)

    def _extract_configs(self, cluster):
        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)
        for ng in cluster.node_groups:
            #TODO(aignatov): setup_script should be replaced with remote calls
            ng.extra = {
                'xml': c_helper.generate_xml_configs(ng.configuration,
                                                     nn.hostname,
                                                     jt.hostname
                                                     if jt else None),
                'setup_script': c_helper.render_template(
                    'setup-general.sh',
                    args={
                        'env_configs': c_helper.extract_environment_confs(
                            ng.configuration)
                    }
                )
            }

    def _push_configs_to_nodes(self, cluster):
        for ng in cluster.node_groups:
            for inst in ng.instances:
                inst.remote.write_file_to('/etc/hadoop/core-site.xml',
                                          ng.extra['xml']['core-site'])
                inst.remote.write_file_to('/etc/hadoop/mapred-site.xml',
                                          ng.extra['xml']['mapred-site'])
                inst.remote.write_file_to('/etc/hadoop/hdfs-site.xml',
                                          ng.extra['xml']['hdfs-site'])
                inst.remote.write_file_to('/tmp/savanna-hadoop-init.sh',
                                          ng.extra['setup_script'])
                inst.remote.execute_command(
                    'sudo chmod 0500 /tmp/savanna-hadoop-init.sh'
                )
                inst.remote.execute_command(
                    'sudo /tmp/savanna-hadoop-init.sh '
                    '>> /tmp/savanna-hadoop-init.log 2>&1')

        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)

        nn.remote.write_file_to('/etc/hadoop/slaves',
                                utils.generate_host_names(
                                utils.get_datanodes(cluster)))
        nn.remote.write_file_to('/etc/hadoop/masters',
                                utils.generate_host_names(
                                utils.get_secondarynamenodes(cluster)))
        nn.remote.execute_command(
            "sudo su -c 'hadoop namenode -format' hadoop")

        if jt and nn.instance_id != jt.instance_id:
            jt.remote.write_file_to('/etc/hadoop/slaves',
                                    utils.generate_host_names(
                                    utils.get_tasktrackers(cluster)))
