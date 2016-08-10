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
import sahara.plugins.mapr.util.validation_utils as vu
from sahara.swift import swift_helper
from sahara.topology import topology_helper as topo


RESOURCE_MANAGER = np.NodeProcess(
    name='resourcemanager',
    ui_name='ResourceManager',
    package='mapr-resourcemanager',
    open_ports=[8033, 8032, 8031, 8030, 8088]
)
NODE_MANAGER = np.NodeProcess(
    name='nodemanager',
    ui_name='NodeManager',
    package='mapr-nodemanager',
    open_ports=[8041, 8040, 8042, 8044]
)
HISTORY_SERVER = np.NodeProcess(
    name='historyserver',
    ui_name='HistoryServer',
    package='mapr-historyserver',
    open_ports=[10020, 19888, 19890]
)


class YARN(s.Service):
    cluster_mode = 'yarn'

    def __init__(self):
        super(YARN, self).__init__()
        self._name = 'hadoop'
        self._ui_name = 'YARN'
        self._node_processes = [RESOURCE_MANAGER, NODE_MANAGER, HISTORY_SERVER]
        self._ui_info = [
            ('NodeManager', NODE_MANAGER, {s.SERVICE_UI: 'http://%s:8042'}),
            ('ResourceManager', RESOURCE_MANAGER,
             {s.SERVICE_UI: 'http://%s:8088'}),
            ('HistoryServer', RESOURCE_MANAGER,
             {s.SERVICE_UI: 'http://%s:19888'}),
        ]
        self._cluster_defaults = ['yarn-cluster.json']
        self._node_defaults = ['yarn-node.json']

    def get_config_files(self, cluster_context, configs, instance=None):
        # yarn-site.xml
        yarn_site = bcf.HadoopXML("yarn-site.xml")
        yarn_site.remote_path = self.conf_dir(cluster_context)
        if instance:
            yarn_site.fetch(instance)
        yarn_site.add_properties(self._get_yarn_site_props(cluster_context))
        yarn_site.load_properties(configs)

        # core-site.xml
        core_site = bcf.HadoopXML("core-site.xml")
        core_site.remote_path = self.conf_dir(cluster_context)
        if instance:
            core_site.fetch(instance)
        core_site.add_properties(self._get_core_site_props(cluster_context))

        return [yarn_site, core_site]

    def _get_core_site_props(self, cluster_context):
        result = {
            'hadoop.proxyuser.mapr.groups': '*',
            'hadoop.proxyuser.mapr.hosts': '*',
        }
        if cluster_context.is_node_aware:
            result.update(self._get_core_site_node_aware_props())
        for conf in swift_helper.get_swift_configs():
            result[conf['name']] = conf['value']
        return result

    def _get_core_site_node_aware_props(self):
        result = topo.vm_awareness_core_config()
        result = {c['name']: c['value'] for c in result}
        result.update({
            'net.topology.script.file.name': '/opt/mapr/topology.sh',
            'net.topology.script.number.args': '75',
        })
        return result

    def _get_yarn_site_props(self, cluster_context):
        return {
            'hadoop.proxyuser.mapr.groups': '*',
            'hadoop.proxyuser.mapr.hosts': '*',
        }

    def conf_dir(self, cluster_context):
        return '%s/etc/hadoop' % self.home_dir(cluster_context)

    def get_file_path(self, file_name):
        template = 'plugins/mapr/services/yarn/resources/%s'
        return template % file_name


class YARNv241(YARN):
    def __init__(self):
        super(YARNv241, self).__init__()
        self._version = '2.4.1'
        self._validation_rules = [
            vu.exactly(1, RESOURCE_MANAGER),
            vu.at_least(1, NODE_MANAGER),
            vu.exactly(1, HISTORY_SERVER),
        ]


class YARNv251(YARN):
    def __init__(self):
        super(YARNv251, self).__init__()
        self._version = '2.5.1'
        self._validation_rules = [
            vu.at_least(1, RESOURCE_MANAGER),
            vu.at_least(1, NODE_MANAGER),
            vu.exactly(1, HISTORY_SERVER),
        ]


class YARNv270(YARN):
    def __init__(self):
        super(YARNv270, self).__init__()
        self._version = "2.7.0"
        self._validation_rules = [
            vu.at_least(1, RESOURCE_MANAGER),
            vu.at_least(1, NODE_MANAGER),
            vu.exactly(1, HISTORY_SERVER),
        ]
