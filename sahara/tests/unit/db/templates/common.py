# Copyright 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six


class Command(object):
    def __init__(self, option_values):
        for k, v in six.iteritems(option_values):
            setattr(self, k, v)


class Config(object):
    def __init__(self, option_values=None):
        self.command = Command(option_values or {})


class Logger(object):
    def __init__(self):
        self.clear_log()

    def warning(self, message):
        self.warnings.append(message)

    def info(self, message):
        self.infos.append(message)

    def debug(self, message):
        pass

    def clear_log(self):
        self.warnings = []
        self.infos = []


SAMPLE_NGT = {
    "plugin_name": "test_plugin",
    "flavor_id": "42",
    "tenant_id": "tenant_1",
    "hadoop_version": "test_version",
    "name": "ngt_test",
    "node_processes": ["p1", "p2"],
    "floating_ip_pool": None,
    "availability_zone": None,
    "node_configs": {
        "service_1": {
            "config_1": "value_1"
        },
        "service_2": {
            "config_1": "value_1"
        },
    },
    "is_default": True
}

SAMPLE_CLT = {
    "plugin_name": "test_plugin",
    "tenant_id": "tenant_1",
    "hadoop_version": "test_version",
    "name": "clt-test",
    "cluster_configs": {
        "service_1": {
            "config_1": "value_1"
        },
        "service_2": {
            "config_1": "value_1"
        }
    },
    "node_groups": [
        {
            "name": "ng_1",
            "flavor_id": "42",
            "node_processes": ["p1", "p2"],
            "count": 1,
            "floating_ip_pool": None,
            "security_groups": None,
            "availability_zone": None,
        }
    ],
    "is_default": True
}

SAMPLE_CLUSTER = {
    "name": "test_cluster",
    "plugin_name": "test_plugin",
    "hadoop_version": "test_version",
    "tenant_id": "tenant_1",
    "node_groups": [
        {
            "name": "ng_1",
            "node_group_template_id": "ng_1_id",
            "count": 1,
        }
    ]
}
