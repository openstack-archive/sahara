# Copyright (c) 2015 Mirantis Inc.
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

from sahara import exceptions as exc
from sahara.i18n import _
from sahara.plugins.ambari import common as p_common
from sahara.plugins import exceptions as pex
from sahara.plugins import kerberos
from sahara.plugins import utils as plugin_utils
from sahara.service.edp import hdfs_helper
from sahara.service.edp.oozie import engine as oozie_engine
from sahara.service.edp.spark import engine as spark_engine


def _get_lib_location(instance, lib_name):
    with instance.remote() as r:
        code, jar_path = r.execute_command(
            ('find /usr/hdp -name "{lib_name}" 2>/dev/null '
             '-print | head -n 1'.format(lib_name=lib_name)),
            run_as_root=True)
    # drop last whitespace character
    return jar_path.rstrip()


def _get_hadoop_openstack_jar_location(instance):
    return _get_lib_location(instance, "hadoop-openstack*.jar")


def _get_jackson_core(instance):
    return _get_lib_location(instance, "jackson-core-asl-1.9*.jar")


class EDPOozieEngine(oozie_engine.OozieJobEngine):
    def get_hdfs_user(self):
        return "oozie"

    def get_client(self):
        if kerberos.is_kerberos_security_enabled(self.cluster):
            return super(EDPOozieEngine, self).get_remote_client()
        return super(EDPOozieEngine, self).get_client()

    def create_hdfs_dir(self, remote, dir_name):
        hdfs_helper.create_dir_hadoop2(remote, dir_name, self.get_hdfs_user())

    def get_oozie_server_uri(self, cluster):
        oozie = plugin_utils.get_instance(cluster, p_common.OOZIE_SERVER)
        return "http://%s:11000/oozie" % oozie.management_ip

    def get_name_node_uri(self, cluster):
        namenodes = plugin_utils.get_instances(cluster, p_common.NAMENODE)
        if len(namenodes) == 1:
            return "hdfs://%s:8020" % namenodes[0].fqdn()
        else:
            return "hdfs://hdfs-ha"

    def get_resource_manager_uri(self, cluster):
        resourcemanagers = plugin_utils.get_instances(cluster,
                                                      p_common.RESOURCEMANAGER)
        return "%s:8050" % resourcemanagers[0].fqdn()

    def get_oozie_server(self, cluster):
        return plugin_utils.get_instance(cluster, p_common.OOZIE_SERVER)

    def validate_job_execution(self, cluster, job, data):
        oozie_count = plugin_utils.get_instances_count(cluster,
                                                       p_common.OOZIE_SERVER)
        if oozie_count != 1:
            raise pex.InvalidComponentCountException(
                p_common.OOZIE_SERVER, "1", oozie_count)
        super(EDPOozieEngine, self).validate_job_execution(cluster, job, data)

    @staticmethod
    def get_possible_job_config(job_type):
        return {"job_config": []}


class EDPSparkEngine(spark_engine.SparkJobEngine):
    edp_base_version = "2.2"

    def __init__(self, cluster):
        super(EDPSparkEngine, self).__init__(cluster)
        # searching for spark instance
        self.master = plugin_utils.get_instance(
            cluster, p_common.SPARK_JOBHISTORYSERVER)
        self.plugin_params["spark-user"] = "sudo -u spark "
        self.plugin_params["spark-submit"] = "spark-submit"
        self.plugin_params["deploy-mode"] = "cluster"
        self.plugin_params["master"] = "yarn-cluster"

    @staticmethod
    def edp_supported(version):
        return version >= EDPSparkEngine.edp_base_version

    def run_job(self, job_execution):
        # calculate class-path dynamically
        driver_classpath = [
            _get_hadoop_openstack_jar_location(self.master),
            _get_jackson_core(self.master)]
        self.plugin_params['driver-class-path'] = ":".join(driver_classpath)
        self.plugin_params['drivers-to-jars'] = driver_classpath

        return super(EDPSparkEngine, self).run_job(job_execution)

    def validate_job_execution(self, cluster, job, data):
        if not self.edp_supported(cluster.hadoop_version):
            raise exc.InvalidDataException(
                _('Ambari plugin of {base} or higher required to run {type} '
                  'jobs').format(
                    base=EDPSparkEngine.edp_base_version, type=job.type))

        spark_nodes_count = plugin_utils.get_instances_count(
            cluster, p_common.SPARK_JOBHISTORYSERVER)
        if spark_nodes_count != 1:
            raise pex.InvalidComponentCountException(
                p_common.SPARK_JOBHISTORYSERVER, '1', spark_nodes_count)

        super(EDPSparkEngine, self).validate_job_execution(
            cluster, job, data)
