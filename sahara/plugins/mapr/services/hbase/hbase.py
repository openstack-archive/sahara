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


HBASE_MASTER = np.NodeProcess(
    name='hbmaster',
    ui_name='HBase-Master',
    package='mapr-hbase-master',
    open_ports=[60000, 60010]
)
HBASE_REGION_SERVER = np.NodeProcess(
    name='hbregionserver',
    ui_name='HBase-RegionServer',
    package='mapr-hbase-regionserver',
    open_ports=[60020]
)
HBASE_THRIFT = np.NodeProcess(
    name='hbasethrift',
    ui_name='HBase-Thrift',
    package='mapr-hbasethrift',
    open_ports=[9090]
)
HBASE_REST = np.NodeProcess(
    name="hbaserestgateway",
    ui_name="HBase REST",
    package="mapr-hbase-rest",
    open_ports=[8080, 8085],
)


class HBase(s.Service):
    def __init__(self):
        super(HBase, self).__init__()
        self._name = 'hbase'
        self._ui_name = 'HBase'
        self._node_processes = [
            HBASE_MASTER,
            HBASE_REGION_SERVER,
            HBASE_THRIFT,
        ]
        self._cluster_defaults = ['hbase-default.json']
        self._validation_rules = [
            vu.at_least(1, HBASE_MASTER),
            vu.at_least(1, HBASE_REGION_SERVER),
        ]
        self._ui_info = [
            ("HBase Master", HBASE_MASTER, {s.SERVICE_UI: "http://%s:60010"}),
        ]

    def get_config_files(self, cluster_context, configs, instance=None):
        hbase_site = bcf.HadoopXML("hbase-site.xml")
        hbase_site.remote_path = self.conf_dir(cluster_context)
        if instance:
            hbase_site.fetch(instance)
        hbase_site.load_properties(configs)
        return [hbase_site]


class HBaseV094(HBase):
    def __init__(self):
        super(HBaseV094, self).__init__()
        self._version = '0.94.24'
        self._dependencies = [('mapr-hbase', self.version)]


class HBaseV0987(HBase):
    def __init__(self):
        super(HBaseV0987, self).__init__()
        self._version = '0.98.7'
        self._dependencies = [('mapr-hbase', self.version)]


class HBaseV0989(HBase):
    def __init__(self):
        super(HBaseV0989, self).__init__()
        self._version = '0.98.9'
        self._dependencies = [('mapr-hbase', self.version)]
        self._node_processes.append(HBASE_REST)
        self._ui_info.append(
            ("HBase REST", HBASE_REST, {s.SERVICE_UI: "http://%s:8085"}),
        )


class HBaseV09812(HBase):
    def __init__(self):
        super(HBaseV09812, self).__init__()
        self._version = "0.98.12"
        self._dependencies = [("mapr-hbase", self.version)]
        self._node_processes.append(HBASE_REST)
        self._ui_info.append(
            ("HBase REST", HBASE_REST, {s.SERVICE_UI: "http://%s:8085"}),
        )


class HBaseV111(HBase):
    def __init__(self):
        super(HBaseV111, self).__init__()
        self._version = "1.1.1"
        self._dependencies = [("mapr-hbase", self.version)]
        self._node_processes.append(HBASE_REST)
        self._ui_info.append(
            ("HBase REST", HBASE_REST, {s.SERVICE_UI: "http://%s:8085"}),
        )
