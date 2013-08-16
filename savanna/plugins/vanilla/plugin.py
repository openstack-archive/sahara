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
from savanna.plugins.general import exceptions as ex
from savanna.plugins.general import utils
from savanna.plugins import provisioning as p
from savanna.plugins.vanilla import config_helper as c_helper
from savanna.plugins.vanilla import run_scripts as run
from savanna.plugins.vanilla import scaling as sc
from savanna.utils import crypto


LOG = logging.getLogger(__name__)


class VanillaProvider(p.ProvisioningPluginBase):
    def __init__(self):
        self.processes = {
            "HDFS": ["namenode", "datanode", "secondarynamenode"],
            "MapReduce": ["tasktracker", "jobtracker"]
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
        if nn_count != 1:
            raise ex.NotSingleNameNodeException(nn_count)

        jt_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "jobtracker")])

        if jt_count not in [0, 1]:
            raise ex.NotSingleJobTrackerException(jt_count)

        tt_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "tasktracker")])
        if jt_count == 0 and tt_count > 0:
            raise ex.TaskTrackersWithoutJobTracker()

    def update_infra(self, cluster):
        pass

    def configure_cluster(self, cluster):
        self._extract_configs(cluster)
        self._push_configs_to_nodes(cluster)
        self._write_hadoop_user_keys(cluster.private_key,
                                     utils.get_instances(cluster))

    def start_cluster(self, cluster):
        nn_instance = utils.get_namenode(cluster)
        datanodes = utils.get_datanodes(cluster)
        jt_instance = utils.get_jobtracker(cluster)
        tasktrackers = utils.get_tasktrackers(cluster)

        with nn_instance.remote as remote:
            run.format_namenode(remote)
            run.start_process(remote, "namenode")

        snns = utils.get_secondarynamenodes(cluster)
        if snns:
            for snn in snns:
                run.start_process(snn.remote, "secondarynamenode")
        for dn in datanodes:
            run.start_process(dn.remote, "datanode")
        LOG.info("HDFS service at '%s' has been started",
                 nn_instance.hostname)

        if jt_instance:
            run.start_process(jt_instance.remote, "jobtracker")
            for tt in tasktrackers:
                run.start_process(tt.remote, "tasktracker")
            LOG.info("MapReduce service at '%s' has been started",
                     jt_instance.hostname)

        LOG.info('Cluster %s has been started successfully' % cluster.name)
        self._set_cluster_info(cluster)

    def _extract_configs(self, cluster):
        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)

        for ng in cluster.node_groups:
            ng.extra = {
                'xml': c_helper.generate_xml_configs(ng.configuration,
                                                     ng.storage_paths,
                                                     nn.hostname,
                                                     jt.hostname
                                                     if jt else None),
                'setup_script': c_helper.generate_setup_script(
                    ng.storage_paths,
                    c_helper.extract_environment_confs(ng.configuration)
                )
            }

    def decommission_nodes(self, cluster, instances):
        tts = utils.get_tasktrackers(cluster)
        dns = utils.get_datanodes(cluster)
        decommission_dns = False
        decommission_tts = False

        for i in instances:
            if 'datanode' in i.node_group.node_processes:
                dns.remove(i)
                decommission_dns = True
            if 'tasktracker' in i.node_group.node_processes:
                tts.remove(i)
                decommission_tts = True

        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)

        if decommission_tts:
            sc.decommission_tt(jt, instances, tts)
        if decommission_dns:
            sc.decommission_dn(nn, instances, dns)

    def validate_scaling(self, cluster, existing, additional):
        self._validate_existing_ng_scaling(cluster, existing)
        self._validate_additional_ng_scaling(cluster, additional)

    def scale_cluster(self, cluster, instances):
        self._extract_configs(cluster)
        self._push_configs_to_nodes(cluster, instances=instances)
        self._write_hadoop_user_keys(cluster.private_key,
                                     instances)
        run.refresh_nodes(utils.get_namenode(cluster).remote, "dfsadmin")
        jt = utils.get_jobtracker(cluster)
        if jt:
            run.refresh_nodes(jt.remote, "mradmin")

        for i in instances:
            with i.remote as remote:
                if "datanode" in i.node_group.node_processes:
                    run.start_process(remote, "datanode")

                if "tasktracker" in i.node_group.node_processes:
                    run.start_process(remote, "tasktracker")

    def _push_configs_to_nodes(self, cluster, instances=None):
        if instances is None:
            instances = utils.get_instances(cluster)

        for inst in instances:
            files = {
                '/etc/hadoop/core-site.xml': inst.node_group.extra['xml'][
                    'core-site'],
                '/etc/hadoop/mapred-site.xml': inst.node_group.extra['xml'][
                    'mapred-site'],
                '/etc/hadoop/hdfs-site.xml': inst.node_group.extra['xml'][
                    'hdfs-site'],
                '/tmp/savanna-hadoop-init.sh': inst.node_group.extra[
                    'setup_script']
            }
            with inst.remote as r:
                r.execute_command(
                    'sudo chown -R $USER:$USER /etc/hadoop'
                )
                r.write_files_to(files)
                r.execute_command(
                    'sudo chmod 0500 /tmp/savanna-hadoop-init.sh'
                )
                r.execute_command(
                    'sudo /tmp/savanna-hadoop-init.sh '
                    '>> /tmp/savanna-hadoop-init.log 2>&1')

        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)

        with nn.remote as r:
            r.write_file_to('/etc/hadoop/dn.incl', utils.
                            generate_fqdn_host_names(
                            utils.get_datanodes(cluster)))
        if jt:
            with jt.remote as r:
                r.write_file_to('/etc/hadoop/tt.incl', utils.
                                generate_fqdn_host_names(
                                utils.get_tasktrackers(cluster)))

    def _set_cluster_info(self, cluster):
        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)

        info = cluster.info

        if jt and jt.management_ip:
            info['MapReduce'] = {
                'Web UI': 'http://%s:50030' % jt.management_ip
            }
        if nn and nn.management_ip:
            info['HDFS'] = {
                'Web UI': 'http://%s:50070' % nn.management_ip
            }

    def _write_hadoop_user_keys(self, private_key, instances):
        public_key = crypto.private_key_to_public_key(private_key)

        files = {
            'id_rsa': private_key,
            'authorized_keys': public_key
        }

        mv_cmd = 'sudo mkdir -p /home/hadoop/.ssh/; ' \
                 'sudo mv id_rsa authorized_keys /home/hadoop/.ssh ; ' \
                 'sudo chown -R hadoop:hadoop /home/hadoop/.ssh; ' \
                 'sudo chmod 600 /home/hadoop/.ssh/{id_rsa,authorized_keys}'

        for instance in instances:
            with instance.remote as remote:
                remote.write_files_to(files)
                remote.execute_command(mv_cmd)

    def _get_scalable_processes(self):
        return ["datanode", "tasktracker"]

    def _validate_additional_ng_scaling(self, cluster, additional):
        jt = utils.get_jobtracker(cluster)
        scalable_processes = self._get_scalable_processes()

        for ng in additional:
            if not set(ng.node_processes).issubset(scalable_processes):
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, "Vanilla plugin cannot scale nodegroup"
                             " with processes: " +
                             ' '.join(ng.node_processes))
            if not jt and 'tasktracker' in ng.node_processes:
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, "Vanilla plugin cannot scale node group with "
                             "processes which have no master-processes run "
                             "in cluster")

    def _validate_existing_ng_scaling(self, cluster, existing):
        ng_names = existing.copy()
        scalable_processes = self._get_scalable_processes()
        dn_to_delete = 0
        for ng in cluster.node_groups:
            if ng.name in existing:
                del ng_names[ng.name]
                if ng.count > existing[ng.name] and "datanode" in \
                        ng.node_processes:
                    dn_to_delete += ng.count - existing[ng.name]
                if not set(ng.node_processes).issubset(scalable_processes):
                    raise ex.NodeGroupCannotBeScaled(
                        ng.name, "Vanilla plugin cannot scale nodegroup"
                                 " with processes: " +
                                 ' '.join(ng.node_processes))

        dn_amount = len(utils.get_datanodes(cluster))
        rep_factor = c_helper.determine_cluster_config(cluster,
                                                       "dfs.replication")

        if dn_to_delete > 0 and dn_amount - dn_to_delete < rep_factor:
            raise Exception("Vanilla plugin cannot shrink cluster because "
                            "it would be not enough nodes for replicas "
                            "(replication factor is %s )" % rep_factor)

        if len(ng_names) != 0:
            raise ex.NodeGroupsDoNotExist(ng_names.keys())
