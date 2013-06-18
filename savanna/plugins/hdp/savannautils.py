# Copyright (c) 2013 Hortonworks, Inc.
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

import savanna.db.models as m
from savanna.plugins import provisioning as p


def convert(cluster_template, normalized_config):
    cluster_template.hadoop_version = normalized_config.hadoop_version
    for ng in normalized_config.node_groups:
        ct_node_group = m.NodeGroup(ng.name, ng.flavor,
                                    ng.node_processes,
                                    ng.count)
        cluster_template.node_groups.append(ct_node_group)
    for entry in normalized_config.cluster_configs:
        ci = entry.config
        ct_config = {"config": p.Config(ci.name, ci.applicable_target,
                     ci.scope, config_type=ci.type,
                     default_value=ci.default_value,
                     is_optional=ci.is_optional,
                     description=ci.description),
                     "value": entry.value}
        cluster_template.cluster_configs.append(ct_config)

    return cluster_template
