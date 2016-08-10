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

import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.hbase.hbase as hbase
import sahara.plugins.mapr.services.hive.hive as hive
import sahara.plugins.mapr.util.maprfs_helper as mfs
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.utils.files as files

SPARK_SLAVE_UI_PORT = 8081
SPARK_HS_UI_PORT = 18080

LOG = logging.getLogger(__name__)

SPARK_HISTORY_SERVER = np.NodeProcess(
    name='spark-historyserver',
    ui_name='Spark HistoryServer',
    package='mapr-spark-historyserver',
    open_ports=[SPARK_HS_UI_PORT]
)
SPARK_SLAVE = np.NodeProcess(
    name='spark-master',
    ui_name='Spark Slave',
    package='mapr-spark',
    open_ports=[SPARK_SLAVE_UI_PORT]
)


class SparkOnYarn(s.Service):
    JAR_FILE_TARGET = '/apps/spark/lib'
    MFS_DIR = '/apps/spark'
    SERVLET_JAR = 'javax.servlet-api.jar'

    def __init__(self):
        super(SparkOnYarn, self).__init__()
        self._name = 'spark'
        self._ui_name = 'Spark'
        self._version = '1.5.2'
        self._dependencies = [('mapr-spark', self.version)]
        self._node_processes = [
            SPARK_HISTORY_SERVER,
            SPARK_SLAVE,
        ]
        self._validation_rules = [
            vu.exactly(1, SPARK_HISTORY_SERVER),
            vu.at_least(1, SPARK_SLAVE),
        ]
        self._ui_info = [
            ('Spark History Server', SPARK_HISTORY_SERVER,
             {s.SERVICE_UI: 'http://%%s:%s' % SPARK_HS_UI_PORT})]

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
                                  hive_version + '.0')
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
        self.copy_assembly_jar_to_mfs(cluster_context)
        self._copy_hive_site(cluster_context)
        self._copy_hbase_site(cluster_context)
        self._copy_jar_from_hue(cluster_context)

    def copy_assembly_jar_to_mfs(self, cluster_context):
        target = self.JAR_FILE_TARGET
        hdfs_user = 'mapr'
        with cluster_context.get_instance(SPARK_HISTORY_SERVER).remote() as r:
            mfs.copy_from_local(r, self._assembly_jar_path(cluster_context),
                                target, hdfs_user)

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
        hive_datanucleus_libs = self._hive_datanucleus_libs_path(context)
        hive_libs = self._hive_libs_path(context)
        hadoop_libs = self._hadoop_libs_path(context)
        hive_datanucleus_libs.insert(0, hive_site)
        mfs_paths = self._hive_datanucleus_libs_path(context)
        return {
            'spark.yarn.dist.files': ','.join(mfs_paths),
            'spark.sql.hive.metastore.version': hive_version + '.0',
            'spark.sql.hive.metastore.jars': ':'.join(hadoop_libs + hive_libs)
        }

    def _hadoop_libs_path(self, context):
        cmd = 'echo $(hadoop classpath)'
        with context.get_instance(SPARK_HISTORY_SERVER).remote() as r:
            result = r.execute_command(cmd, run_as_root=True, timeout=600)
        return result[1].replace('\n', '').split(':')

    def _hive_libs_path(self, context):
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

    def _hive_datanucleus_libs_path(self, context):
        cmd = "find %s -name 'datanucleus-*.jar'" % (
            self._hive(context).home_dir(context) + '/lib')
        with context.get_instance(hive.HIVE_METASTORE).remote() as r:
            result = r.execute_command(cmd, run_as_root=True, timeout=600)
        return [x for x in list(result[1].split('\n')) if x]

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

    def _get_hbase_version(self, cluster_context):
        return (self._hbase(cluster_context).version
                if self._hbase(cluster_context) else None)

    def _get_hive_version(self, cluster_context):
        return (self._hive(cluster_context).version
                if self._hive(cluster_context) else None)

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
