# Copyright (c) 2014 Hoang Do, Phuc Vo, P. Michiardi, D. Venzano
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

import os

from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor
from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.plugins import exceptions as ex
from sahara.plugins import provisioning as p
from sahara.plugins.spark import config_helper as c_helper
from sahara.plugins.spark import edp_engine
from sahara.plugins.spark import run_scripts as run
from sahara.plugins.spark import scaling as sc
from sahara.plugins import utils
from sahara.topology import topology_helper as th
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import files as f
from sahara.utils import general as ug
from sahara.utils import remote


conductor = conductor.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class SparkProvider(p.ProvisioningPluginBase):
    def __init__(self):
        self.processes = {
            "HDFS": ["namenode", "datanode"],
            "Spark": ["master", "slave"]
        }

    def get_title(self):
        return "Apache Spark"

    def get_description(self):
        return _("This plugin provides an ability to launch Spark on Hadoop "
                 "CDH cluster without any management consoles.")

    def get_versions(self):
        return ['1.0.0', '0.9.1']

    def get_configs(self, hadoop_version):
        return c_helper.get_plugin_configs()

    def get_node_processes(self, hadoop_version):
        return self.processes

    def validate(self, cluster):
        nn_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "namenode")])
        if nn_count != 1:
            raise ex.InvalidComponentCountException("namenode", 1, nn_count)

        dn_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "datanode")])
        if dn_count < 1:
            raise ex.InvalidComponentCountException("datanode", _("1 or more"),
                                                    nn_count)

        rep_factor = c_helper.get_config_value('HDFS', "dfs.replication",
                                               cluster)
        if dn_count < rep_factor:
            raise ex.InvalidComponentCountException(
                'datanode', _('%s or more') % rep_factor, dn_count,
                _('Number of %(dn)s instances should not be less '
                  'than %(replication)s')
                % {'dn': 'datanode', 'replication': 'dfs.replication'})

        # validate Spark Master Node and Spark Slaves
        sm_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "master")])

        if sm_count != 1:
            raise ex.RequiredServiceMissingException("Spark master")

        sl_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "slave")])

        if sl_count < 1:
            raise ex.InvalidComponentCountException("Spark slave",
                                                    _("1 or more"),
                                                    sl_count)

    def update_infra(self, cluster):
        pass

    def configure_cluster(self, cluster):
        self._setup_instances(cluster)

    @cpo.event_wrapper(
        True, step=utils.start_process_event_message("NameNode"))
    def _start_namenode(self, nn_instance):
        with remote.get_remote(nn_instance) as r:
            run.format_namenode(r)
            run.start_processes(r, "namenode")

    def start_spark(self, cluster):
        sm_instance = utils.get_instance(cluster, "master")
        if sm_instance:
            self._start_spark(cluster, sm_instance)

    @cpo.event_wrapper(
        True, step=utils.start_process_event_message("SparkMasterNode"))
    def _start_spark(self, cluster, sm_instance):
        with remote.get_remote(sm_instance) as r:
            run.start_spark_master(r, self._spark_home(cluster))
            LOG.info(_LI("Spark service at {host} has been started").format(
                     host=sm_instance.hostname()))

    def start_cluster(self, cluster):
        nn_instance = utils.get_instance(cluster, "namenode")
        dn_instances = utils.get_instances(cluster, "datanode")

        # Start the name node
        self._start_namenode(nn_instance)

        # start the data nodes
        self._start_datanode_processes(dn_instances)

        LOG.info(_LI("Hadoop services in cluster {cluster} have been started")
                 .format(cluster=cluster.name))

        with remote.get_remote(nn_instance) as r:
            r.execute_command("sudo -u hdfs hdfs dfs -mkdir -p /user/$USER/")
            r.execute_command("sudo -u hdfs hdfs dfs -chown $USER "
                              "/user/$USER/")

        # start spark nodes
        self.start_spark(cluster)

        LOG.info(_LI('Cluster {cluster} has been started successfully').format(
                 cluster=cluster.name))
        self._set_cluster_info(cluster)

    def _spark_home(self, cluster):
        return c_helper.get_config_value("Spark", "Spark home", cluster)

    def _extract_configs_to_extra(self, cluster):
        nn = utils.get_instance(cluster, "namenode")
        sp_master = utils.get_instance(cluster, "master")
        sp_slaves = utils.get_instances(cluster, "slave")

        extra = dict()

        config_master = config_slaves = ''
        if sp_master is not None:
            config_master = c_helper.generate_spark_env_configs(cluster)

        if sp_slaves is not None:
            slavenames = []
            for slave in sp_slaves:
                slavenames.append(slave.hostname())
            config_slaves = c_helper.generate_spark_slaves_configs(slavenames)
        else:
            config_slaves = "\n"

        # Any node that might be used to run spark-submit will need
        # these libs for swift integration
        config_defaults = c_helper.generate_spark_executor_classpath(cluster)

        extra['job_cleanup'] = c_helper.generate_job_cleanup_config(cluster)
        for ng in cluster.node_groups:
            extra[ng.id] = {
                'xml': c_helper.generate_xml_configs(
                    ng.configuration(),
                    ng.storage_paths(),
                    nn.hostname(), None
                ),
                'setup_script': c_helper.generate_hadoop_setup_script(
                    ng.storage_paths(),
                    c_helper.extract_hadoop_environment_confs(
                        ng.configuration())
                ),
                'sp_master': config_master,
                'sp_slaves': config_slaves,
                'sp_defaults': config_defaults
            }

        if c_helper.is_data_locality_enabled(cluster):
            topology_data = th.generate_topology_map(
                cluster, CONF.enable_hypervisor_awareness)
            extra['topology_data'] = "\n".join(
                [k + " " + v for k, v in topology_data.items()]) + "\n"

        return extra

    def _start_datanode_processes(self, dn_instances):
        if len(dn_instances) == 0:
            return

        cpo.add_provisioning_step(
            dn_instances[0].cluster_id,
            utils.start_process_event_message("DataNodes"), len(dn_instances))

        with context.ThreadGroup() as tg:
            for i in dn_instances:
                tg.spawn('spark-start-dn-%s' % i.instance_name,
                         self._start_datanode, i)

    @cpo.event_wrapper(mark_successful_on_exit=True)
    def _start_datanode(self, instance):
        with instance.remote() as r:
            run.start_processes(r, "datanode")

    def _setup_instances(self, cluster, instances=None):
        extra = self._extract_configs_to_extra(cluster)

        if instances is None:
            instances = utils.get_instances(cluster)

        self._push_configs_to_nodes(cluster, extra, instances)

    def _push_configs_to_nodes(self, cluster, extra, new_instances):
        all_instances = utils.get_instances(cluster)
        cpo.add_provisioning_step(
            cluster.id, _("Push configs to nodes"), len(all_instances))
        with context.ThreadGroup() as tg:
            for instance in all_instances:
                if instance in new_instances:
                    tg.spawn('spark-configure-%s' % instance.instance_name,
                             self._push_configs_to_new_node, cluster,
                             extra, instance)
                else:
                    tg.spawn('spark-reconfigure-%s' % instance.instance_name,
                             self._push_configs_to_existing_node, cluster,
                             extra, instance)

    @cpo.event_wrapper(mark_successful_on_exit=True)
    def _push_configs_to_new_node(self, cluster, extra, instance):
        ng_extra = extra[instance.node_group.id]

        files_hadoop = {
            os.path.join(c_helper.HADOOP_CONF_DIR,
                         "core-site.xml"): ng_extra['xml']['core-site'],
            os.path.join(c_helper.HADOOP_CONF_DIR,
                         "hdfs-site.xml"): ng_extra['xml']['hdfs-site'],
        }

        sp_home = self._spark_home(cluster)
        files_spark = {
            os.path.join(sp_home, 'conf/spark-env.sh'): ng_extra['sp_master'],
            os.path.join(sp_home, 'conf/slaves'): ng_extra['sp_slaves'],
            os.path.join(sp_home,
                         'conf/spark-defaults.conf'): ng_extra['sp_defaults']
        }

        files_init = {
            '/tmp/sahara-hadoop-init.sh': ng_extra['setup_script'],
            'id_rsa': cluster.management_private_key,
            'authorized_keys': cluster.management_public_key
        }

        # pietro: This is required because the (secret) key is not stored in
        # .ssh which hinders password-less ssh required by spark scripts
        key_cmd = ('sudo cp $HOME/id_rsa $HOME/.ssh/; '
                   'sudo chown $USER $HOME/.ssh/id_rsa; '
                   'sudo chmod 600 $HOME/.ssh/id_rsa')

        storage_paths = instance.node_group.storage_paths()
        dn_path = ' '.join(c_helper.make_hadoop_path(storage_paths,
                                                     '/dfs/dn'))
        nn_path = ' '.join(c_helper.make_hadoop_path(storage_paths,
                                                     '/dfs/nn'))

        hdfs_dir_cmd = ('sudo mkdir -p %(nn_path)s %(dn_path)s &&'
                        'sudo chown -R hdfs:hadoop %(nn_path)s %(dn_path)s &&'
                        'sudo chmod 755 %(nn_path)s %(dn_path)s' %
                        {"nn_path": nn_path, "dn_path": dn_path})

        with remote.get_remote(instance) as r:
            r.execute_command(
                'sudo chown -R $USER:$USER /etc/hadoop'
            )
            r.execute_command(
                'sudo chown -R $USER:$USER %s' % sp_home
            )
            r.write_files_to(files_hadoop)
            r.write_files_to(files_spark)
            r.write_files_to(files_init)
            r.execute_command(
                'sudo chmod 0500 /tmp/sahara-hadoop-init.sh'
            )
            r.execute_command(
                'sudo /tmp/sahara-hadoop-init.sh '
                '>> /tmp/sahara-hadoop-init.log 2>&1')

            r.execute_command(hdfs_dir_cmd)
            r.execute_command(key_cmd)

            if c_helper.is_data_locality_enabled(cluster):
                r.write_file_to(
                    '/etc/hadoop/topology.sh',
                    f.get_file_text(
                        'plugins/spark/resources/topology.sh'))
                r.execute_command(
                    'sudo chmod +x /etc/hadoop/topology.sh'
                )

            self._write_topology_data(r, cluster, extra)
            self._push_master_configs(r, cluster, extra, instance)
            self._push_cleanup_job(r, cluster, extra, instance)

    @cpo.event_wrapper(mark_successful_on_exit=True)
    def _push_configs_to_existing_node(self, cluster, extra, instance):
        node_processes = instance.node_group.node_processes
        need_update_hadoop = (c_helper.is_data_locality_enabled(cluster) or
                              'namenode' in node_processes)
        need_update_spark = ('master' in node_processes or
                             'slave' in node_processes)

        if need_update_spark:
            ng_extra = extra[instance.node_group.id]
            sp_home = self._spark_home(cluster)
            files = {
                os.path.join(sp_home,
                             'conf/spark-env.sh'): ng_extra['sp_master'],
                os.path.join(sp_home, 'conf/slaves'): ng_extra['sp_slaves'],
                os.path.join(
                    sp_home,
                    'conf/spark-defaults.conf'): ng_extra['sp_defaults']
            }
            r = remote.get_remote(instance)
            r.write_files_to(files)
            self._push_cleanup_job(r, cluster, extra, instance)
        if need_update_hadoop:
            with remote.get_remote(instance) as r:
                self._write_topology_data(r, cluster, extra)
                self._push_master_configs(r, cluster, extra, instance)

    def _write_topology_data(self, r, cluster, extra):
        if c_helper.is_data_locality_enabled(cluster):
            topology_data = extra['topology_data']
            r.write_file_to('/etc/hadoop/topology.data', topology_data)

    def _push_master_configs(self, r, cluster, extra, instance):
        node_processes = instance.node_group.node_processes
        if 'namenode' in node_processes:
            self._push_namenode_configs(cluster, r)

    def _push_cleanup_job(self, r, cluster, extra, instance):
        node_processes = instance.node_group.node_processes
        if 'master' in node_processes:
            if extra['job_cleanup']['valid']:
                r.write_file_to('/etc/hadoop/tmp-cleanup.sh',
                                extra['job_cleanup']['script'])
                r.execute_command("chmod 755 /etc/hadoop/tmp-cleanup.sh")
                cmd = 'sudo sh -c \'echo "%s" > /etc/cron.d/spark-cleanup\''
                r.execute_command(cmd % extra['job_cleanup']['cron'])
            else:
                r.execute_command("sudo rm -f /etc/hadoop/tmp-cleanup.sh")
                r.execute_command("sudo rm -f /etc/crond.d/spark-cleanup")

    def _push_namenode_configs(self, cluster, r):
        r.write_file_to('/etc/hadoop/dn.incl',
                        utils.generate_fqdn_host_names(
                            utils.get_instances(cluster, "datanode")))
        r.write_file_to('/etc/hadoop/dn.excl', '')

    def _set_cluster_info(self, cluster):
        nn = utils.get_instance(cluster, "namenode")
        sp_master = utils.get_instance(cluster, "master")
        info = {}

        if nn:
            address = c_helper.get_config_value(
                'HDFS', 'dfs.http.address', cluster)
            port = address[address.rfind(':') + 1:]
            info['HDFS'] = {
                'Web UI': 'http://%s:%s' % (nn.management_ip, port)
            }
            info['HDFS']['NameNode'] = 'hdfs://%s:8020' % nn.hostname()

        if sp_master:
            port = c_helper.get_config_value(
                'Spark', 'Master webui port', cluster)
            if port is not None:
                info['Spark'] = {
                    'Web UI': 'http://%s:%s' % (sp_master.management_ip, port)
                }
        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})

    # Scaling

    def validate_scaling(self, cluster, existing, additional):
        self._validate_existing_ng_scaling(cluster, existing)
        self._validate_additional_ng_scaling(cluster, additional)

    def decommission_nodes(self, cluster, instances):
        sls = utils.get_instances(cluster, "slave")
        dns = utils.get_instances(cluster, "datanode")
        decommission_dns = False
        decommission_sls = False

        for i in instances:
            if 'datanode' in i.node_group.node_processes:
                dns.remove(i)
                decommission_dns = True
            if 'slave' in i.node_group.node_processes:
                sls.remove(i)
                decommission_sls = True

        nn = utils.get_instance(cluster, "namenode")
        spark_master = utils.get_instance(cluster, "master")

        if decommission_sls:
            sc.decommission_sl(spark_master, instances, sls)
        if decommission_dns:
            sc.decommission_dn(nn, instances, dns)

    def scale_cluster(self, cluster, instances):
        master = utils.get_instance(cluster, "master")
        r_master = remote.get_remote(master)

        run.stop_spark(r_master, self._spark_home(cluster))

        self._setup_instances(cluster, instances)
        nn = utils.get_instance(cluster, "namenode")
        run.refresh_nodes(remote.get_remote(nn), "dfsadmin")
        dn_instances = [instance for instance in instances if
                        'datanode' in instance.node_group.node_processes]
        self._start_datanode_processes(dn_instances)

        run.start_spark_master(r_master, self._spark_home(cluster))
        LOG.info(_LI("Spark master service at {host} has been restarted")
                 .format(host=master.hostname()))

    def _get_scalable_processes(self):
        return ["datanode", "slave"]

    def _validate_additional_ng_scaling(self, cluster, additional):
        scalable_processes = self._get_scalable_processes()

        for ng_id in additional:
            ng = ug.get_by_id(cluster.node_groups, ng_id)
            if not set(ng.node_processes).issubset(scalable_processes):
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, _("Spark plugin cannot scale nodegroup"
                               " with processes: %s") %
                    ' '.join(ng.node_processes))

    def _validate_existing_ng_scaling(self, cluster, existing):
        scalable_processes = self._get_scalable_processes()
        dn_to_delete = 0
        for ng in cluster.node_groups:
            if ng.id in existing:
                if ng.count > existing[ng.id] and ("datanode" in
                                                   ng.node_processes):
                    dn_to_delete += ng.count - existing[ng.id]
                if not set(ng.node_processes).issubset(scalable_processes):
                    raise ex.NodeGroupCannotBeScaled(
                        ng.name, _("Spark plugin cannot scale nodegroup"
                                   " with processes: %s") %
                        ' '.join(ng.node_processes))

        dn_amount = len(utils.get_instances(cluster, "datanode"))
        rep_factor = c_helper.get_config_value('HDFS', "dfs.replication",
                                               cluster)

        if dn_to_delete > 0 and dn_amount - dn_to_delete < rep_factor:
            raise ex.ClusterCannotBeScaled(
                cluster.name, _("Spark plugin cannot shrink cluster because "
                                "there would be not enough nodes for HDFS "
                                "replicas (replication factor is %s)") %
                rep_factor)

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.EdpEngine.get_supported_job_types():
            return edp_engine.EdpEngine(cluster)

        return None

    def get_open_ports(self, node_group):
        cluster = node_group.cluster
        ports_map = {
            'namenode': [8020, 50070, 50470],
            'datanode': [50010, 1004, 50075, 1006, 50020],
            'master': [
                int(c_helper.get_config_value("Spark", "Master port",
                                              cluster)),
                int(c_helper.get_config_value("Spark", "Master webui port",
                                              cluster)),
            ],
            'slave': [
                int(c_helper.get_config_value("Spark", "Worker webui port",
                                              cluster))
            ]
        }

        ports = []
        for process in node_group.node_processes:
            if process in ports_map:
                ports.extend(ports_map[process])

        return ports
