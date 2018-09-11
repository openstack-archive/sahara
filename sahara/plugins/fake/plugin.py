# Copyright (c) 2014 Mirantis Inc.
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

from sahara import context
from sahara.i18n import _
from sahara.plugins import exceptions as pex
from sahara.plugins.fake import edp_engine
from sahara.plugins import kerberos as krb
from sahara.plugins import provisioning as p
from sahara.plugins import utils as plugin_utils


class FakePluginProvider(p.ProvisioningPluginBase):

    def get_title(self):
        return "Fake Plugin"

    def get_description(self):
        return _("It's a fake plugin that aimed to work on the CirrOS images. "
                 "It doesn't install Hadoop. It's needed to be able to test "
                 "provisioning part of Sahara codebase itself.")

    def get_versions(self):
        return ["0.1"]

    def get_labels(self):
        return {
            'plugin_labels': {
                'enabled': {'status': True},
                'hidden': {'status': True},
            },
            'version_labels': {
                '0.1': {'enabled': {'status': True}}
            }
        }

    def get_node_processes(self, hadoop_version):
        return {
            "HDFS": ["namenode", "datanode"],
            "MapReduce": ["tasktracker", "jobtracker"],
            "Kerberos": [],
        }

    def get_configs(self, hadoop_version):
        # returning kerberos configs
        return krb.get_config_list()

    def configure_cluster(self, cluster):
        with context.ThreadGroup() as tg:
            for instance in plugin_utils.get_instances(cluster):
                tg.spawn('fake-write-%s' % instance.id,
                         self._write_ops, instance)

    def start_cluster(self, cluster):
        self.deploy_kerberos(cluster)
        with context.ThreadGroup() as tg:
            for instance in plugin_utils.get_instances(cluster):
                tg.spawn('fake-check-%s' % instance.id,
                         self._check_ops, instance)

    def deploy_kerberos(self, cluster):
        all_instances = plugin_utils.get_instances(cluster)
        namenodes = plugin_utils.get_instances(cluster, 'namenode')
        server = None
        if len(namenodes) > 0:
            server = namenodes[0]
        elif len(all_instances) > 0:
            server = all_instances[0]
        if server:
            krb.deploy_infrastructure(cluster, server)

    def scale_cluster(self, cluster, instances):
        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('fake-scaling-%s' % instance.id,
                         self._all_check_ops, instance)

    def decommission_nodes(self, cluster, instances):
        pass

    def _write_ops(self, instance):
        with instance.remote() as r:
            # check typical SSH command
            r.execute_command('echo "Hello, world!"')
            # check write file
            data_1 = "sp@m"
            r.write_file_to('test_data', data_1, run_as_root=True)
            # check append file
            data_2 = " and eggs"
            r.append_to_file('test_data', data_2, run_as_root=True)
            # check replace string
            r.replace_remote_string('test_data', "eggs", "pony")

    def _check_ops(self, instance):
        expected_data = "sp@m and pony"
        with instance.remote() as r:
            actual_data = r.read_file_from('test_data', run_as_root=True)

            if actual_data.strip() != expected_data.strip():
                raise pex.HadoopProvisionError("ACTUAL:\n%s\nEXPECTED:\n%s" % (
                    actual_data, expected_data))

    def _all_check_ops(self, instance):
        self._write_ops(instance)
        self._check_ops(instance)

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.FakeJobEngine.get_supported_job_types():
            return edp_engine.FakeJobEngine()

    def get_edp_job_types(self, versions=None):
        res = {}
        for vers in self.get_versions():
            if not versions or vers in versions:
                res[vers] = edp_engine.FakeJobEngine.get_supported_job_types()
        return res

    def get_edp_config_hints(self, job_type, version):
        if version in self.get_versions():
            return edp_engine.FakeJobEngine.get_possible_job_config(job_type)
