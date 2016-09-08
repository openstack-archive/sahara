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

from sahara.plugins import kerberos


def setup_kerberos_for_cluster(cluster, cloudera_utils):
    if kerberos.is_kerberos_security_enabled(cluster):
        manager = cloudera_utils.pu.get_manager(cluster)
        kerberos.deploy_infrastructure(cluster, manager)
        cloudera_utils.full_cluster_stop(cluster)
        kerberos.prepare_policy_files(cluster)
        cloudera_utils.push_kerberos_configs(cluster)
        cloudera_utils.full_cluster_start(cluster)
        kerberos.create_keytabs_for_map(
            cluster,
            {'hdfs': cloudera_utils.pu.get_hdfs_nodes(cluster),
             'spark': [cloudera_utils.pu.get_spark_historyserver(cluster)]})


def prepare_scaling_kerberized_cluster(cluster, cloudera_utils, instances):
    if kerberos.is_kerberos_security_enabled(cluster):
        server = None
        if not kerberos.using_existing_kdc(cluster):
            server = cloudera_utils.pu.get_manager(cluster)
        kerberos.setup_clients(cluster, server)
        kerberos.prepare_policy_files(cluster)
        # manager can correctly handle updating configs
        cloudera_utils.push_kerberos_configs(cluster)
        kerberos.create_keytabs_for_map(
            cluster,
            {'hdfs': cloudera_utils.pu.get_hdfs_nodes(cluster, instances)})
