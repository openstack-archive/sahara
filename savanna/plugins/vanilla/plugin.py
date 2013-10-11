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

from oslo.config import cfg

from savanna import conductor
from savanna import context
from savanna.openstack.common import log as logging
from savanna.openstack.common import uuidutils
from savanna.plugins.general import exceptions as ex
from savanna.plugins.general import utils
from savanna.plugins import provisioning as p
from savanna.plugins.vanilla import config_helper as c_helper
from savanna.plugins.vanilla import run_scripts as run
from savanna.plugins.vanilla import scaling as sc
from savanna.topology import topology_helper as th
from savanna.utils import files as f
from savanna.utils import remote


conductor = conductor.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class VanillaProvider(p.ProvisioningPluginBase):
    def __init__(self):
        self.processes = {
            "HDFS": ["namenode", "datanode", "secondarynamenode"],
            "MapReduce": ["tasktracker", "jobtracker"],
            "JobFlow": ["oozie"],
            "Hive": ["hiveserver"]
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
            "1.2.1 cluster without any management consoles. Also it can "
            "deploy Oozie 4.0.0 and Hive 0.11.0")

    def get_versions(self):
        return ['1.2.1']

    def get_configs(self, hadoop_version):
        return c_helper.get_plugin_configs()

    def get_hive_config_path(self):
        return "/opt/hive/conf/hive-site.xml"

    def get_hdfs_user(self):
        return 'hadoop'

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

        oozie_count = sum([ng.count for ng
                           in utils.get_node_groups(cluster, "oozie")])

        if oozie_count not in [0, 1]:
            raise ex.NotSingleOozieException(oozie_count)

        hive_count = sum([ng.count for ng
                          in utils.get_node_groups(cluster, "hiveserver")])
        if jt_count == 0:

            tt_count = sum([ng.count for ng
                            in utils.get_node_groups(cluster, "tasktracker")])
            if tt_count > 0:
                raise ex.TaskTrackersWithoutJobTracker()

            if oozie_count > 0:
                raise ex.OozieWithoutJobTracker()

            if hive_count > 0:
                raise ex.HiveWithoutJobTracker()

        if hive_count not in [0, 1]:
            raise ex.NotSingleHiveException(hive_count)

    def update_infra(self, cluster):
        pass

    def configure_cluster(self, cluster):
        instances = utils.get_instances(cluster)

        self._setup_instances(cluster, instances)

    def start_cluster(self, cluster):
        instances = utils.get_instances(cluster)
        nn_instance = utils.get_namenode(cluster)
        jt_instance = utils.get_jobtracker(cluster)
        oozie = utils.get_oozie(cluster)
        hive_server = utils.get_hiveserver(cluster)

        with remote.get_remote(nn_instance) as r:
            run.format_namenode(r)
            run.start_processes(r, "namenode")

        for snn in utils.get_secondarynamenodes(cluster):
            run.start_processes(remote.get_remote(snn), "secondarynamenode")

        if jt_instance:
            run.start_processes(remote.get_remote(jt_instance), "jobtracker")

        self._start_tt_dn_processes(instances)

        LOG.info("Hadoop services in cluster %s have been started" %
                 cluster.name)

        if oozie:
            with remote.get_remote(oozie) as r:
                if c_helper.is_mysql_enable(cluster):
                    run.mysql_start(r, oozie)
                    run.oozie_create_db(r)
                run.oozie_share_lib(r, nn_instance.hostname)
                run.start_oozie(r)
                LOG.info("Oozie service at '%s' has been started",
                         nn_instance.hostname)

        if hive_server:
            with remote.get_remote(nn_instance) as r:
                run.hive_create_warehouse_dir(r)
            if c_helper.is_mysql_enable(cluster):
                with remote.get_remote(hive_server) as h:
                    if not oozie or hive_server.hostname != oozie.hostname:
                        run.mysql_start(h, hive_server)
                    run.hive_create_db(h)
                    run.hive_metastore_start(h)
                LOG.info("Hive Metastore server at %s has been started",
                         hive_server.hostname)

        LOG.info('Cluster %s has been started successfully' % cluster.name)
        self._set_cluster_info(cluster)

    def _extract_configs_to_extra(self, cluster):
        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)
        oozie = utils.get_oozie(cluster)
        hive = utils.get_hiveserver(cluster)

        extra = dict()

        if hive:
            extra['hive_mysql_passwd'] = uuidutils.generate_uuid()

        for ng in cluster.node_groups:
            extra[ng.id] = {
                'xml': c_helper.generate_xml_configs(
                    ng.configuration,
                    ng.storage_paths,
                    nn.hostname,
                    jt.hostname if jt else None,
                    oozie.hostname if oozie else None,
                    hive.hostname if hive else None,
                    extra['hive_mysql_passwd'] if hive else None),
                'setup_script': c_helper.generate_setup_script(
                    ng.storage_paths,
                    c_helper.extract_environment_confs(ng.configuration),
                    append_oozie=(
                        oozie is not None and oozie.node_group.id == ng.id)
                )
            }

        if c_helper.is_data_locality_enabled(cluster):
            topology_data = th.generate_topology_map(
                cluster, CONF.enable_hypervisor_awareness)
            extra['topology_data'] = "\n".join(
                [k + " " + v for k, v in topology_data.items()]) + "\n"

        return extra

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
        self._setup_instances(cluster, instances)

        run.refresh_nodes(remote.get_remote(
            utils.get_namenode(cluster)), "dfsadmin")
        jt = utils.get_jobtracker(cluster)
        if jt:
            run.refresh_nodes(remote.get_remote(jt), "mradmin")

        self._start_tt_dn_processes(instances)

    def _start_tt_dn_processes(self, instances):
        tt_dn_names = ["datanode", "tasktracker"]

        with context.ThreadGroup() as tg:
            for i in instances:
                processes = set(i.node_group.node_processes)
                tt_dn_procs = processes.intersection(tt_dn_names)

                if tt_dn_procs:
                    tg.spawn('vanilla-start-tt-dn-%s' % i.instance_name,
                             self._start_tt_dn, i, list(tt_dn_procs))

    def _start_tt_dn(self, instance, tt_dn_procs):
        with instance.remote as r:
            run.start_processes(r, *tt_dn_procs)

    def _setup_instances(self, cluster, instances):
        extra = self._extract_configs_to_extra(cluster)
        self._push_configs_to_nodes(cluster, extra, instances)

    def _push_configs_to_nodes(self, cluster, extra, new_instances):
        all_instances = utils.get_instances(cluster)
        with context.ThreadGroup() as tg:
            for instance in all_instances:
                if instance in new_instances:
                    tg.spawn('vanilla-configure-%s' % instance.instance_name,
                             self._push_configs_to_new_node, cluster,
                             extra, instance)
                else:
                    tg.spawn('vanilla-reconfigure-%s' % instance.instance_name,
                             self._push_configs_to_existing_node, cluster,
                             extra, instance)

    def _push_configs_to_new_node(self, cluster, extra, instance):
        ng_extra = extra[instance.node_group.id]

        files = {
            '/etc/hadoop/core-site.xml': ng_extra['xml']['core-site'],
            '/etc/hadoop/mapred-site.xml': ng_extra['xml']['mapred-site'],
            '/etc/hadoop/hdfs-site.xml': ng_extra['xml']['hdfs-site'],
            '/tmp/savanna-hadoop-init.sh': ng_extra['setup_script'],
            'id_rsa': cluster.management_private_key,
            'authorized_keys': cluster.management_public_key
        }

        key_cmd = 'sudo mkdir -p /home/hadoop/.ssh/; ' \
                  'sudo mv id_rsa authorized_keys /home/hadoop/.ssh ; ' \
                  'sudo chown -R hadoop:hadoop /home/hadoop/.ssh; ' \
                  'sudo chmod 600 /home/hadoop/.ssh/{id_rsa,authorized_keys}'

        with remote.get_remote(instance) as r:
            # TODO(aignatov): sudo chown is wrong solution. But it works.
            r.execute_command(
                'sudo chown -R $USER:$USER /etc/hadoop'
            )
            r.execute_command(
                'sudo chown -R $USER:$USER /opt/oozie/conf'
            )
            r.write_files_to(files)
            r.execute_command(
                'sudo chmod 0500 /tmp/savanna-hadoop-init.sh'
            )
            r.execute_command(
                'sudo /tmp/savanna-hadoop-init.sh '
                '>> /tmp/savanna-hadoop-init.log 2>&1')

            r.execute_command(key_cmd)

            if c_helper.is_data_locality_enabled(cluster):
                r.write_file_to(
                    '/etc/hadoop/topology.sh',
                    f.get_file_text(
                        'plugins/vanilla/resources/topology.sh'))
                r.execute_command(
                    'sudo chmod +x /etc/hadoop/topology.sh'
                )

            self._write_topology_data(r, cluster, extra)
            self._push_master_configs(r, cluster, extra, instance)

    def _push_configs_to_existing_node(self, cluster, extra, instance):
        node_processes = instance.node_group.node_processes
        need_update = (c_helper.is_data_locality_enabled(cluster) or
                       'namenode' in node_processes or
                       'jobtracker' in node_processes or
                       'oozie' in node_processes or
                       'hiveserver' in node_processes)

        if not need_update:
            return

        with remote.get_remote(instance) as r:
            self._write_topology_data(r, cluster, extra)
            self._push_master_configs(r, cluster, extra, instance)

    def _write_topology_data(self, r, cluster, extra):
        if c_helper.is_data_locality_enabled(cluster):
            topology_data = extra['topology_data']
            r.write_file_to('/etc/hadoop/topology.data', topology_data)

    def _push_master_configs(self, r, cluster, extra, instance):
        ng_extra = extra[instance.node_group.id]
        node_processes = instance.node_group.node_processes

        if 'namenode' in node_processes:
            self._push_namenode_configs(cluster, r)

        if 'jobtracker' in node_processes:
            self._push_jobtracker_configs(cluster, r)

        if 'oozie' in node_processes:
            self._push_oozie_configs(cluster, ng_extra, r)

        if 'hiveserver' in node_processes:
            self._push_hive_configs(cluster, ng_extra,
                                    extra['hive_mysql_passwd'], r)

    def _push_namenode_configs(self, cluster, r):
        r.write_file_to('/etc/hadoop/dn.incl', utils.
                        generate_fqdn_host_names(
                        utils.get_datanodes(cluster)))

    def _push_jobtracker_configs(self, cluster, r):
        r.write_file_to('/etc/hadoop/tt.incl', utils.
                        generate_fqdn_host_names(
                        utils.get_tasktrackers(cluster)))

    def _push_oozie_configs(self, cluster, ng_extra, r):
        r.write_file_to('/opt/oozie/conf/oozie-site.xml',
                        ng_extra['xml']['oozie-site'])

        if c_helper.is_mysql_enable(cluster):
            sql_script = f.get_file_text(
                'plugins/vanilla/resources/create_oozie_db.sql')
            files = {
                '/tmp/create_oozie_db.sql': sql_script
            }
            r.write_files_to(files)

    def _push_hive_configs(self, cluster, ng_extra, hive_mysql_passwd, r):
        files = {
            '/opt/hive/conf/hive-site.xml':
            ng_extra['xml']['hive-site']
        }
        if c_helper.is_mysql_enable(cluster):
            sql_script = f.get_file_text(
                'plugins/vanilla/resources/create_hive_db.sql'
            )
            sql_script = sql_script.replace('pass',
                                            hive_mysql_passwd)
            files.update({'/tmp/create_hive_db.sql': sql_script})
        r.write_files_to(files)

    def _set_cluster_info(self, cluster):
        nn = utils.get_namenode(cluster)
        jt = utils.get_jobtracker(cluster)
        oozie = utils.get_oozie(cluster)
        info = {}

        if jt:
            info['MapReduce'] = {
                'Web UI': 'http://%s:50030' % jt.management_ip
            }

        if nn:
            info['HDFS'] = {
                'Web UI': 'http://%s:50070' % nn.management_ip
            }

        if oozie:
            info['JobFlow'] = {
                'Oozie': 'http://%s:11000' % oozie.management_ip
            }

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})

    def _get_scalable_processes(self):
        return ["datanode", "tasktracker"]

    def _get_by_id(self, lst, id):
        for obj in lst:
            if obj.id == id:
                return obj

        return None

    def _validate_additional_ng_scaling(self, cluster, additional):
        jt = utils.get_jobtracker(cluster)
        scalable_processes = self._get_scalable_processes()

        for ng_id in additional:
            ng = self._get_by_id(cluster.node_groups, ng_id)
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
        scalable_processes = self._get_scalable_processes()
        dn_to_delete = 0
        for ng in cluster.node_groups:
            if ng.id in existing:
                if ng.count > existing[ng.id] and "datanode" in \
                        ng.node_processes:
                    dn_to_delete += ng.count - existing[ng.id]
                if not set(ng.node_processes).issubset(scalable_processes):
                    raise ex.NodeGroupCannotBeScaled(
                        ng.name, "Vanilla plugin cannot scale nodegroup"
                                 " with processes: " +
                                 ' '.join(ng.node_processes))

        dn_amount = len(utils.get_datanodes(cluster))
        rep_factor = c_helper.determine_cluster_config(cluster, 'HDFS',
                                                       "dfs.replication")

        if dn_to_delete > 0 and dn_amount - dn_to_delete < rep_factor:
            raise ex.ClusterCannotBeScaled(
                cluster.name, "Vanilla plugin cannot shrink cluster because "
                              "it would be not enough nodes for replicas "
                              "(replication factor is %s)" % rep_factor)
