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

from oslo.config import cfg

from sahara import conductor
from sahara import context
from sahara.openstack.common import log as logging
from sahara.plugins.general import exceptions as ex
from sahara.plugins.general import utils
from sahara.plugins import provisioning as p
from sahara.plugins.spark import config_helper as c_helper
from sahara.plugins.spark import run_scripts as run
from sahara.topology import topology_helper as th
from sahara.utils import files as f
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
        return (
            "This plugin provides an ability to launch Spark on Hadoop "
            "CDH cluster without any management consoles.")

    def get_versions(self):
        return ['0.9.1']

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
            raise ex.InvalidComponentCountException("datanode", "1 or more",
                                                    nn_count)

        # validate Spark Master Node and Spark Slaves
        sm_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "master")])

        if sm_count != 1:
            raise ex.RequiredServiceMissingException("Spark master")

        sl_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "slave")])

        if sl_count < 1:
            raise ex.InvalidComponentCountException("Spark slave", "1 or more",
                                                    sl_count)

    def update_infra(self, cluster):
        pass

    def configure_cluster(self, cluster):
        self._setup_instances(cluster)

    def start_cluster(self, cluster):
        nn_instance = utils.get_instance(cluster, "namenode")
        sm_instance = utils.get_instance(cluster, "master")
        dn_instances = utils.get_instances(cluster, "datanode")

        # Start the name node
        with remote.get_remote(nn_instance) as r:
            run.format_namenode(r)
            run.start_processes(r, "namenode")

        # start the data nodes
        self._start_slave_datanode_processes(dn_instances)

        LOG.info("Hadoop services in cluster %s have been started" %
                 cluster.name)

        with remote.get_remote(nn_instance) as r:
            r.execute_command("sudo -u hdfs hdfs dfs -mkdir -p /user/$USER/")
            r.execute_command("sudo -u hdfs hdfs dfs -chown $USER \
                              /user/$USER/")

        # start spark nodes
        if sm_instance:
            with remote.get_remote(sm_instance) as r:
                run.start_spark_master(r)
                LOG.info("Spark service at '%s' has been started",
                         sm_instance.hostname())

        LOG.info('Cluster %s has been started successfully' % cluster.name)
        self._set_cluster_info(cluster)

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

        for ng in cluster.node_groups:
            extra[ng.id] = {
                'xml': c_helper.generate_xml_configs(
                    ng.configuration(),
                    ng.storage_paths(),
                    nn.hostname(), None,
                ),
                'setup_script': c_helper.generate_hadoop_setup_script(
                    ng.storage_paths(),
                    c_helper.extract_hadoop_environment_confs(
                        ng.configuration())
                ),
                'sp_master': config_master,
                'sp_slaves': config_slaves
            }

        if c_helper.is_data_locality_enabled(cluster):
            topology_data = th.generate_topology_map(
                cluster, CONF.enable_hypervisor_awareness)
            extra['topology_data'] = "\n".join(
                [k + " " + v for k, v in topology_data.items()]) + "\n"

        return extra

    def validate_scaling(self, cluster, existing, additional):
        raise ex.ClusterCannotBeScaled("Scaling Spark clusters has not been"
                                       "implemented yet")

    def decommission_nodes(self, cluster, instances):
        pass

    def scale_cluster(self, cluster, instances):
        pass

    def _start_slave_datanode_processes(self, dn_instances):
        with context.ThreadGroup() as tg:
            for i in dn_instances:
                tg.spawn('spark-start-dn-%s' % i.instance_name,
                         self._start_datanode, i)

    def _start_datanode(self, instance):
        with instance.remote() as r:
            run.start_processes(r, "datanode")

    def _setup_instances(self, cluster):
        extra = self._extract_configs_to_extra(cluster)

        instances = utils.get_instances(cluster)
        self._push_configs_to_nodes(cluster, extra, instances)

    def _push_configs_to_nodes(self, cluster, extra, new_instances):
        all_instances = utils.get_instances(cluster)
        with context.ThreadGroup() as tg:
            for instance in all_instances:
                if instance in new_instances:
                    tg.spawn('spark-configure-%s' % instance.instance_name,
                             self._push_configs_to_new_node, cluster,
                             extra, instance)

    def _push_configs_to_new_node(self, cluster, extra, instance):
        ng_extra = extra[instance.node_group.id]

        files_hadoop = {
            '/etc/hadoop/conf/core-site.xml': ng_extra['xml']['core-site'],
            '/etc/hadoop/conf/hdfs-site.xml': ng_extra['xml']['hdfs-site'],
        }

        files_spark = {
            '/opt/spark/conf/spark-env.sh': ng_extra['sp_master'],
            '/opt/spark/conf/slaves': ng_extra['sp_slaves']
        }

        files_init = {
            '/tmp/sahara-hadoop-init.sh': ng_extra['setup_script'],
            'id_rsa': cluster.management_private_key,
            'authorized_keys': cluster.management_public_key
        }

        # pietro: This is required because the (secret) key is not stored in
        # .ssh which hinders password-less ssh required by spark scripts
        key_cmd = 'sudo cp $HOME/id_rsa $HOME/.ssh/; '\
            'sudo chown $USER $HOME/.ssh/id_rsa; '\
            'sudo chmod 600 $HOME/.ssh/id_rsa'

        for ng in cluster.node_groups:
            dn_path = c_helper.extract_hadoop_path(ng.storage_paths(),
                                                   '/dfs/dn')
            nn_path = c_helper.extract_hadoop_path(ng.storage_paths(),
                                                   '/dfs/nn')
            hdfs_dir_cmd = 'sudo mkdir -p %s %s;'\
                'sudo chown -R hdfs:hadoop %s %s;'\
                'sudo chmod 755 %s %s;'\
                % (nn_path, dn_path,
                   nn_path, dn_path,
                   nn_path, dn_path)

        with remote.get_remote(instance) as r:
            r.execute_command(
                'sudo chown -R $USER:$USER /etc/hadoop'
            )
            r.execute_command(
                'sudo chown -R $USER:$USER /opt/spark'
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

    def _write_topology_data(self, r, cluster, extra):
        if c_helper.is_data_locality_enabled(cluster):
            topology_data = extra['topology_data']
            r.write_file_to('/etc/hadoop/topology.data', topology_data)

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
