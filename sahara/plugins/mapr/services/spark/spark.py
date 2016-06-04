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


from oslo_log import log as logging
import six

import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.hbase.hbase as hbase
import sahara.plugins.mapr.services.hive.hive as hive
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.maprfs_helper as mfs
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.utils.files as files

SPARK_MASTER_PORT = 7077
SPARK_MASTER_UI_PORT = 8080
SPARK_SLAVE_UI_PORT = 8081
SPARK_HS_UI_PORT = 18080

LOG = logging.getLogger(__name__)


class SparkNodeProcess(np.NodeProcess):
    pass


class SparkMaster(np.NodeProcess):
    def submit_url(self, cluster_context):
        args = {
            "host": cluster_context.get_instance(self).fqdn(),
            "port": SPARK_MASTER_PORT,
        }

        return "spark://%(host)s:%(port)s" % args


class SparkWorker(SparkNodeProcess):
    def start(self, cluster_context, instances=None):
        start_command = self._get_start_command(cluster_context, run_as="mapr")
        g.execute_command(instances, start_command)

    def stop(self, cluster_context, instances=None):
        stop_command = self._get_stop_command(cluster_context, run_as="mapr")
        g.execute_command(instances, stop_command)

    def _get_start_command(self, cluster_context, run_as=None):
        command_template = ("%(start_script)s 1 %(master_url)s"
                            " --webui-port %(web_ui_port)s")
        args = {
            "master_url": SPARK_MASTER.submit_url(cluster_context),
            "start_script": self._get_start_script_path(cluster_context),
            "web_ui_port": SPARK_SLAVE_UI_PORT,
        }

        return g._run_as(run_as, command_template % args)

    def _get_stop_command(self, cluster_context, run_as=None):
        command_template = ("%(stop_script)s stop"
                            " org.apache.spark.deploy.worker.Worker 1")
        args = {"stop_script": self._get_stop_script_path(cluster_context)}

        return g._run_as(run_as, command_template % args)

    def _get_start_script_path(self, cluster_context):
        path_template = "%(spark_home)s/sbin/start-slave.sh"
        args = {"spark_home": Spark().home_dir(cluster_context)}

        return path_template % args

    def _get_stop_script_path(self, cluster_context):
        path_template = "%(spark_home)s/sbin/spark-daemons.sh"
        args = {"spark_home": Spark().home_dir(cluster_context)}

        return path_template % args


SPARK_MASTER = SparkMaster(
    name='spark-master',
    ui_name='Spark Master',
    package='mapr-spark-master',
    open_ports=[SPARK_MASTER_PORT, SPARK_MASTER_UI_PORT],
)
SPARK_HISTORY_SERVER = SparkNodeProcess(
    name='spark-historyserver',
    ui_name='Spark HistoryServer',
    package='mapr-spark-historyserver',
    open_ports=[SPARK_HS_UI_PORT]
)
SPARK_SLAVE = SparkWorker(
    name='spark-master',
    ui_name='Spark Slave',
    package='mapr-spark',
    open_ports=[SPARK_SLAVE_UI_PORT]
)


class Spark(s.Service):
    def __init__(self):
        super(Spark, self).__init__()
        self._name = 'spark'
        self._ui_name = 'Spark'
        self._version = '1.5.2'
        self._node_processes = [
            SPARK_HISTORY_SERVER,
            SPARK_MASTER,
            SPARK_SLAVE,
        ]
        self._dependencies = [('mapr-spark', self.version)]
        self._ui_info = [
            ('Spark Master', SPARK_MASTER,
             {s.SERVICE_UI: 'http://%%s:%s' % SPARK_MASTER_UI_PORT}),
            ('Spark History Server', SPARK_HISTORY_SERVER,
             {s.SERVICE_UI: 'http://%%s:%s' % SPARK_HS_UI_PORT})]
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
        LOG.debug("SSH keys successfully installed.")

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
        LOG.debug("Spark slaves list successfully written.")

    def _generate_slaves_file(self, cluster_context):
        slaves = cluster_context.get_instances(SPARK_SLAVE)
        return "\n".join(instance.fqdn() for instance in slaves)

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
        LOG.debug("Spark History Server successfully installed.")


class SparkOnYarn(Spark):
    JAR_FILE_TARGET = '/apps/spark/lib'
    MFS_DIR = '/apps/spark'
    SERVLET_JAR = 'javax.servlet-api.jar'

    def __init__(self):
        super(SparkOnYarn, self).__init__()
        self._version = '1.5.2'
        self._node_processes = [
            SPARK_HISTORY_SERVER,
            SPARK_SLAVE,
        ]
        self._validation_rules = [
            vu.exactly(1, SPARK_HISTORY_SERVER),
            vu.at_least(1, SPARK_SLAVE),
        ]

    def _get_hbase_version(self, cluster_context):
        return (self._hbase(cluster_context).version
                if self._hbase(cluster_context) else None)

    def _get_hive_version(self, cluster_context):
        return (self._hive(cluster_context).version
                if self._hive(cluster_context) else None)

    def _get_packages(self, cluster_context, node_processes):
        result = []

        result += self.dependencies
        result += [(np.package, self.version) for np in node_processes]
        hbase_version = self._get_hbase_version(cluster_context)
        hive_version = self._get_hive_version(cluster_context)
        if hbase_version:
            result += [('mapr-hbase', hbase_version)]
        if hive_version:
            result += [('mapr-hive', hive_version)]

        return result

    def get_config_files(self, cluster_context, configs, instance=None):
        hbase_version = self._get_hbase_version(cluster_context)
        hive_version = self._get_hive_version(cluster_context)
        # spark-env-sh
        template = 'plugins/mapr/services/' \
                   'spark/resources/spark-env.template'
        env_sh = bcf.TemplateFile('spark-env.sh')
        env_sh.remote_path = self.conf_dir(cluster_context)
        env_sh.parse(files.get_file_text(template))
        env_sh.add_property('version', self.version)
        env_sh.add_property('servlet_api_jar', self.SERVLET_JAR)

        # spark-defaults
        conf = bcf.PropertiesFile('spark-defaults.conf', separator=' ')
        conf.remote_path = self.conf_dir(cluster_context)
        if instance:
            conf.fetch(instance)
        conf.add_property('spark.yarn.jar', 'maprfs://%s/%s' %
                          (self.JAR_FILE_TARGET,
                           self._assembly_jar_path(cluster_context)
                           .rsplit('/', 1)[1]))

        # compatibility.version
        versions = bcf.PropertiesFile('compatibility.version')
        versions.remote_path = self.home_dir(cluster_context) + '/mapr-util'
        if instance:
            versions.fetch(instance)

        if hive_version:
            versions.add_property('hive_versions',
                                  self._format_hive_version(hive_version))
            conf.add_properties(self._hive_properties(cluster_context))
        if hbase_version:
            versions.add_property('hbase_versions', hbase_version)
            conf.add_property('spark.executor.extraClassPath',
                              '%s/lib/*' % self._hbase(cluster_context)
                              .home_dir(cluster_context))
        return [conf, versions, env_sh]

    def update(self, cluster_context, instances=None):
        pass

    def post_install(self, cluster_context, instances):
        pass

    def configure(self, cluster_context, instances=None):
        pass

    def post_start(self, cluster_context, instances):
        self._create_hadoop_spark_dirs(cluster_context)
        self._copy_jar_files_to_mfs(cluster_context)
        self._copy_hive_site(cluster_context)
        self._copy_hbase_site(cluster_context)
        self._copy_jar_from_hue(cluster_context)

    def _copy_jar_files_to_mfs(self, cluster_context):
        hive_service = self._hive(cluster_context)
        target = self.JAR_FILE_TARGET
        hdfs_user = 'mapr'
        with cluster_context.get_instance(SPARK_HISTORY_SERVER).remote() as r:
            mfs.copy_from_local(r, self._assembly_jar_path(cluster_context),
                                target, hdfs_user)
        # copy hive datanucleus libs and hive-site.xml
        paths = []
        if hive_service:
            hive_conf = self._hive(cluster_context).conf_dir(cluster_context)
            paths.append('%s/hive-site.xml' % hive_conf)
            paths += self._hive_datanucleus_libs_paths(cluster_context)
            with cluster_context.get_instance(
                    hive.HIVE_METASTORE).remote() as r:
                for path in paths:
                    mfs.copy_from_local(r, path, target, hdfs_user)

    def _copy_hive_site(self, cluster_context):
        if not self._hive(cluster_context):
            return
        hive_conf = self._hive(cluster_context).conf_dir(cluster_context)
        with cluster_context.get_instance(hive.HIVE_SERVER_2).remote() as h:
            with cluster_context.get_instance(
                    SPARK_HISTORY_SERVER).remote() as s:
                mfs.exchange(h, s, hive_conf + '/hive-site.xml',
                             self.conf_dir(cluster_context) + '/hive-site.xml',
                             hdfs_user='mapr')

    def _copy_hbase_site(self, cluster_context):
        if not self._hbase(cluster_context):
            return
        hbase_conf = self._hbase(cluster_context).conf_dir(cluster_context)
        with cluster_context.get_instance(hbase.HBASE_MASTER).remote() as h:
            with cluster_context.get_instance(
                    SPARK_HISTORY_SERVER).remote() as s:
                mfs.exchange(h, s, hbase_conf + '/hbase-site.xml',
                             self.conf_dir(
                                 cluster_context) + '/hbase-site.xml',
                             hdfs_user='mapr')

    def _create_hadoop_spark_dirs(self, cluster_context):
        home = '/apps/spark'
        libs = self.JAR_FILE_TARGET
        run_as_user = 'mapr'
        with cluster_context.get_instance(SPARK_HISTORY_SERVER).remote() as r:
            mfs.mkdir(r, home, run_as=run_as_user)
            mfs.mkdir(r, libs, run_as=run_as_user)
            mfs.chmod(r, home, 777, run_as=run_as_user)
            mfs.chmod(r, libs, 777, run_as=run_as_user)

    def _hive_properties(self, context):
        hive_version = self._hive(context).version
        hive_conf = self._hive(context).conf_dir(context)
        hive_site = hive_conf + '/hive-site.xml'
        hive_datanucleus_libs = self._hive_datanucleus_libs_paths(context)
        hive_libs = self._hive_libs_paths(context)
        hadoop_libs = self._hadoop_libs(context)
        hive_datanucleus_libs.insert(0, hive_site)
        mfs_paths = self._hive_datanucleus_libs_mafs_paths(
            hive_datanucleus_libs)
        return {
            'spark.yarn.dist.files': ','.join(mfs_paths),
            'spark.sql.hive.metastore.version': self._format_hive_version(
                hive_version),
            'spark.sql.hive.metastore.jars': ':'.join(hadoop_libs + hive_libs)
        }

    def _hadoop_libs(self, context):
        cmd = 'echo $(hadoop classpath)'
        with context.get_instance(SPARK_HISTORY_SERVER).remote() as r:
            result = r.execute_command(cmd, run_as_root=True, timeout=600)
        return result[1].replace('\n', '').split(':')

    def _hive_libs_paths(self, context):
        cmd = "find %s -name '*.jar'" % (
            self._hive(context).home_dir(context) + '/lib')
        with context.get_instance(hive.HIVE_METASTORE).remote() as r:
            result = r.execute_command(cmd, run_as_root=True, timeout=600)
        return [x for x in list(result[1].split('\n')) if x]

    def _assembly_jar_path(self, context):
        cmd = "find %s -name 'spark-assembly*.jar'" % (
            self.home_dir(context) + '/lib')
        with context.get_instance(SPARK_HISTORY_SERVER).remote() as r:
            result = r.execute_command(cmd, run_as_root=True, timeout=600)
        if result[1]:
            return result[1].strip()
        else:
            raise Exception("no spark-assembly lib found!")

    def _hive_datanucleus_libs_paths(self, context):
        cmd = "find %s -name 'datanucleus-*.jar'" % (
            self._hive(context).home_dir(context) + '/lib')
        with context.get_instance(hive.HIVE_METASTORE).remote() as r:
            result = r.execute_command(cmd, run_as_root=True, timeout=600)
        return [x for x in list(result[1].split('\n')) if x]

    def _hive_datanucleus_libs_mafs_paths(self, local_paths):
        mfs_path = 'maprfs://%s/' % self.JAR_FILE_TARGET
        return list(
            map(lambda path: mfs_path + path.rsplit('/', 1)[1], local_paths))

    def _format_hive_version(self, version):
        return version + '.0'

    # hive installed service instance
    def _hive(self, context):
        hive_instance = context.get_instance(hive.HIVE_SERVER_2)
        if not hive_instance:
            return None
        hive_version = context.get_chosen_service_version('Hive')
        return context._find_service_instance('Hive', hive_version)

    # hbase installed service instance
    def _hbase(self, context):
        hbase_instance = context.get_instance(hbase.HBASE_MASTER)
        if not hbase_instance:
            return None
        hbase_version = context.get_chosen_service_version('HBase')
        return context._find_service_instance('HBase', hbase_version)

    # hue installed service instance
    def _hue(self, context):
        hue_instance = context.get_instance('Hue')
        if not hue_instance:
            return None
        hue_version = context.get_chosen_service_version('Hue')
        return context._find_service_instance('Hue', hue_version)

    def _copy_jar_from_hue(self, context):
        if not self._hue(context):
            return
        jar_path = "%s/apps/spark/java-lib/javax.servlet-api-*.jar" % \
                   self._hue(context).home_dir(context)
        path = '%s/lib/' % self.home_dir(context) + self.SERVLET_JAR
        with context.get_instance('Hue').remote() as r1:
            for instance in context.get_instances(SPARK_SLAVE):
                with instance.remote() as r2:
                    mfs.exchange(r1, r2, jar_path, path, 'mapr')
