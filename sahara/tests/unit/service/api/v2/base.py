# Copyright (c) 2017 EasyStack Inc.
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

from sahara.plugins import base as pl_base
from sahara.plugins import provisioning as pr_base

SAMPLE_CLUSTER = {
    'plugin_name': 'fake',
    'hadoop_version': 'test_version',
    'tenant_id': 'tenant_1',
    'name': 'test_cluster',
    'user_keypair_id': 'my_keypair',
    'node_groups': [
        {
            'auto_security_group': True,
            'name': 'ng_1',
            'flavor_id': '42',
            'node_processes': ['p1', 'p2'],
            'count': 1
        },
        {
            'auto_security_group': False,
            'name': 'ng_2',
            'flavor_id': '42',
            'node_processes': ['p3', 'p4'],
            'count': 3
        },
        {
            'auto_security_group': False,
            'name': 'ng_3',
            'flavor_id': '42',
            'node_processes': ['p3', 'p4'],
            'count': 1
        }
    ],
    'cluster_configs': {
        'service_1': {
            'config_2': 'value_2'
        },
        'service_2': {
            'config_1': 'value_1'
        }
    },
}

SCALE_DATA = {
    'resize_node_groups': [
        {
            'name': 'ng_1',
            'count': 3,
        },
        {
            'name': 'ng_2',
            'count': 2,
        }
    ],
    'add_node_groups': [
        {
            'auto_security_group': True,
            'name': 'ng_4',
            'flavor_id': '42',
            'node_processes': ['p1', 'p2'],
            'count': 1
        },
    ]
}

SCALE_DATA_SPECIFIC_INSTANCE = {
    'resize_node_groups': [
        {
            'name': 'ng_1',
            'count': 3,
        },
        {
            'name': 'ng_2',
            'count': 1,
            'instances': ['ng_2_0']
        }
    ],
    'add_node_groups': []
}

SCALE_DATA_N_SPECIFIC_INSTANCE = {
    'resize_node_groups': [
        {
            'name': 'ng_1',
            'count': 3,
        },
        {
            'name': 'ng_2',
            'count': 1,
            'instances': ['ng_2_0', 'ng_2_2']
        }
    ],
    'add_node_groups': []
}


class FakePlugin(pr_base.ProvisioningPluginBase):
    _info = {}
    name = "fake"

    def __init__(self, calls_order):
        self.calls_order = calls_order

    def configure_cluster(self, cluster):
        pass

    def start_cluster(self, cluster):
        pass

    def get_description(self):
        return "Some description"

    def get_title(self):
        return "Fake plugin"

    def validate(self, cluster):
        self.calls_order.append('validate')

    def get_open_ports(self, node_group):
        self.calls_order.append('get_open_ports')

    def validate_scaling(self, cluster, to_be_enlarged, additional):
        self.calls_order.append('validate_scaling')

    def get_versions(self):
        return ['0.1', '0.2']

    def get_node_processes(self, version):
        return {'HDFS': ['namenode', 'datanode']}

    def get_configs(self, version):
        return []

    def recommend_configs(self, cluster, scaling=False):
        self.calls_order.append('recommend_configs')


class FakePluginManager(pl_base.PluginManager):
    def __init__(self, calls_order):
        super(FakePluginManager, self).__init__()
        self.plugins['fake'] = FakePlugin(calls_order)
