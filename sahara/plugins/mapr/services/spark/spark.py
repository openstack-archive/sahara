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

import six

import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.maprfs_helper as mfs
import sahara.plugins.mapr.util.validation_utils as vu


SPARK_MASTER_PORT = 7077


class SparkNodeProcess(np.NodeProcess):
    pass


class SparkMaster(np.NodeProcess):
    _submit_port = SPARK_MASTER_PORT

    def submit_url(self, cluster_context):
        host = cluster_context.get_instance(self).fqdn()
        args = {'host': host, 'port': self.submit_port(cluster_context)}
        return 'spark://%(host)s:%(port)s' % args

    def submit_port(self, cluster_context):
        return self._submit_port


class SparkWorker(SparkNodeProcess):
    _start_script = 'sbin/start-slave.sh'

    def start(self, cluster_context, instances=None):
        master_url = SPARK_MASTER.submit_url(cluster_context)
        args = {
            'spark_home': Spark().home_dir(cluster_context),
            'start_slave': self._start_script,
            'master_url': master_url,
        }
        command = g._run_as('mapr', '%(start_slave)s 1 %(master_url)s')
        command = ('cd %(spark_home)s && ' + command) % args
        g.execute_command(instances, command)


SPARK_MASTER = SparkMaster(
    name='spark-master',
    ui_name='Spark Master',
    package='mapr-spark-master',
    open_ports=[SPARK_MASTER_PORT],
)
SPARK_HISTORY_SERVER = SparkNodeProcess(
    name='spark-historyserver',
    ui_name='Spark HistoryServer',
    package='mapr-spark-historyserver',
)
SPARK_SLAVE = SparkWorker(
    name='spark-master',
    ui_name='Spark Slave',
    package='mapr-spark',
)


@six.add_metaclass(s.Single)
class Spark(s.Service):
    def __init__(self):
        super(Spark, self).__init__()
        self._name = 'spark'
        self._ui_name = 'Spark'
        self._version = '1.2.1'
        self._node_processes = [
            SPARK_HISTORY_SERVER,
            SPARK_MASTER,
            SPARK_SLAVE,
        ]
        self._dependencies = [('mapr-spark', self.version)]
        self._ui_info = [('SPARK', SPARK_MASTER, 'http://%s:8080')]
        self._validation_rules = [
            vu.exactly(1, SPARK_MASTER),
            vu.exactly(1, SPARK_HISTORY_SERVER),
            vu.at_least(1, SPARK_SLAVE),
        ]
        self._node_defaults = ['spark-default.json']

    def _get_packages(self, node_processes):
        result = []
        result += self.dependencies
        result += [(np.package, self.version)
                   for np in node_processes
                   if np != SPARK_HISTORY_SERVER]
        return g.unique_list(result)

    def get_config_files(self, cluster_context, configs, instance=None):
        env = bcf.EnvironmentConfig('spark-env.sh')
        env.remote_path = self.conf_dir(cluster_context)
        if instance:
            env.fetch(instance)
        env.load_properties(configs)
        env.add_properties(self._get_spark_ha_props(cluster_context))
        env.add_property('SPARK_WORKER_DIR', '/tmp/spark')
        return [env]

    def configure(self, cluster_context, instances=None):
        self._write_slaves_list(cluster_context)

    def update(self, cluster_context, instances=None):
        if cluster_context.changed_instances(SPARK_SLAVE):
            self._write_slaves_list(cluster_context)

    def post_install(self, cluster_context, instances):
        self._install_ssh_keys(cluster_context, instances)

    def post_start(self, cluster_context, instances):
        self._create_hadoop_spark_dirs(cluster_context)
        if cluster_context.filter_instances(instances, SPARK_HISTORY_SERVER):
            self._install_spark_history_server(cluster_context, instances)

    def _install_ssh_keys(self, cluster_context, instances):
        slaves = cluster_context.filter_instances(instances, SPARK_SLAVE)
        masters = cluster_context.filter_instances(instances, SPARK_MASTER)
        instances = g.unique_list(masters + slaves)
        private_key = cluster_context.cluster.management_private_key
        public_key = cluster_context.cluster.management_public_key
        g.execute_on_instances(
            instances, g.install_ssh_key, 'mapr', private_key, public_key)
        g.execute_on_instances(instances, g.authorize_key, 'mapr', public_key)

    def _get_spark_ha_props(self, cluster_context):
        zookeepers = cluster_context.get_zookeeper_nodes_ip_with_port()
        login_conf = '%s/conf/mapr.login.conf' % cluster_context.mapr_home
        props = {
            'spark.deploy.recoveryMode': 'ZOOKEEPER',
            'spark.deploy.zookeeper.url': zookeepers,
            'zookeeper.sasl.client': 'false',
            'java.security.auth.login.config': login_conf,
        }
        props = ' '.join(map(lambda i: '-D%s=%s' % i, six.iteritems(props)))
        return {'SPARK_DAEMON_JAVA_OPTS': props}

    def _write_slaves_list(self, cluster_context):
        path = '%s/slaves' % self.conf_dir(cluster_context)
        data = self._generate_slaves_file(cluster_context)
        master = cluster_context.get_instance(SPARK_MASTER)
        g.write_file(master, path, data, owner='root')

    def _generate_slaves_file(self, cluster_context):
        slaves = cluster_context.get_instances(SPARK_SLAVE)
        return '\n'.join(map(lambda i: i.fqdn(), slaves))

    def _create_hadoop_spark_dirs(self, cluster_context):
        path = '/apps/spark'
        run_as_user = 'mapr'
        with cluster_context.get_instance(SPARK_MASTER).remote() as r:
            mfs.mkdir(r, path, run_as=run_as_user)
            mfs.chmod(r, path, 777, run_as=run_as_user)

    def _install_spark_history_server(self, cluster_context, instances):
        h_servers = cluster_context.filter_instances(
            instances, SPARK_HISTORY_SERVER)
        package = [(SPARK_HISTORY_SERVER.package, self.version)]
        command = cluster_context.distro.create_install_cmd(package)
        g.execute_command(h_servers, command, run_as='root')
