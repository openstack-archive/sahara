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


import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.hive.hive as hive
import sahara.plugins.mapr.util.commands as cmd
import sahara.plugins.mapr.util.maprfs_helper as mfs
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.utils.files as files

IMPALA_SERVER = np.NodeProcess(
    name='impalaserver',
    ui_name='Impala-Server',
    package='mapr-impala-server',
    open_ports=[21000, 21050, 25000]
)
IMPALA_STATE_STORE = np.NodeProcess(
    name='impalastore',
    ui_name='Impala-Statestore',
    package='mapr-impala-statestore',
    open_ports=[25010]
)
IMPALA_CATALOG = np.NodeProcess(
    name='impalacatalog',
    ui_name='Impala-Catalog',
    package='mapr-impala-catalog',
    open_ports=[25020]
)


class Impala(s.Service):
    def __init__(self):
        super(Impala, self).__init__()
        self._name = 'impala'
        self._ui_name = 'Impala'
        self._node_processes = [
            IMPALA_CATALOG,
            IMPALA_SERVER,
            IMPALA_STATE_STORE,
        ]

    def _get_impala_env_props(self, context):
        return {}

    def post_start(self, cluster_context, instances):
        self._copy_hive_site(cluster_context)

    def _copy_hive_site(self, cluster_context):
        hive_site_path = self._hive(cluster_context).conf_dir(
            cluster_context) + "/hive-site.xml"
        path = self.conf_dir(cluster_context) + "/hive-site.xml"
        with cluster_context.get_instance(hive.HIVE_METASTORE).remote() as r1:
            for instance in cluster_context.get_instances(IMPALA_SERVER):
                with instance.remote() as r2:
                    mfs.exchange(r1, r2, hive_site_path, path, 'mapr')
            with cluster_context.get_instance(IMPALA_CATALOG).remote() as r3:
                mfs.exchange(r1, r3, hive_site_path, path, 'mapr')
            with cluster_context.get_instance(
                    IMPALA_STATE_STORE).remote() as r4:
                mfs.exchange(r1, r4, hive_site_path, path, 'mapr')

    # hive service instance
    def _hive(self, context):
        hive_version = context.get_chosen_service_version('Hive')
        return context._find_service_instance('Hive', hive_version)

    def get_config_files(self, cluster_context, configs, instance=None):
        defaults = 'plugins/mapr/services/impala/resources/impala-env.sh.j2'

        impala_env = bcf.TemplateFile("env.sh")
        impala_env.remote_path = self.conf_dir(cluster_context)
        if instance:
            impala_env.fetch(instance)
        impala_env.parse(files.get_file_text(defaults))
        impala_env.add_properties(self._get_impala_env_props(cluster_context))

        return [impala_env]

    def post_install(self, cluster_context, instances):
        impalas = cluster_context.filter_instances(instances, IMPALA_SERVER)
        for instance in impalas:
            cmd.chown(instance, 'mapr:mapr', self.service_dir(cluster_context))


class ImpalaV141(Impala):
    def __init__(self):
        super(ImpalaV141, self).__init__()
        self._version = '1.4.1'
        self._dependencies = [
            ('mapr-hive', hive.HiveV013().version),
            ('mapr-impala', self.version),
        ]
        self._validation_rules = [
            vu.depends_on(hive.HiveV013(), self),
            vu.exactly(1, IMPALA_STATE_STORE),
            vu.exactly(1, IMPALA_CATALOG),
            vu.at_least(1, IMPALA_SERVER),
        ]

    def _get_impala_env_props(self, context):
        return {
            'impala_version': self.version,
            'statestore_host': context.get_instance_ip(IMPALA_STATE_STORE),
            'catalog_host': context.get_instance_ip(IMPALA_CATALOG),
        }


class ImpalaV220(Impala):
    def __init__(self):
        super(ImpalaV220, self).__init__()
        self._version = '2.2.0'
        self._dependencies = [
            ('mapr-hive', hive.HiveV12().version),
            ('mapr-impala', self.version),
        ]
        self._validation_rules = [
            vu.depends_on(hive.HiveV12(), self),
            vu.exactly(1, IMPALA_STATE_STORE),
            vu.exactly(1, IMPALA_CATALOG),
            vu.at_least(1, IMPALA_SERVER),
            vu.required_os('centos', self)
        ]

    def _get_impala_env_props(self, context):
        return {
            'impala_version': self.version,
            'statestore_host': context.get_instance_ip(IMPALA_STATE_STORE),
            'catalog_host': context.get_instance_ip(IMPALA_CATALOG),
        }

    def _get_packages(self, cluster_context, node_processes):
        result = []

        result += self.dependencies
        result += [(np.package, self.version) for np in node_processes]
        # gets the latest version
        hbase_version = cluster_context.get_chosen_service_version('HBase')
        result += [('mapr-hbase', hbase_version)]

        return result
