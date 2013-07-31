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
from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def convert(cluster_template, normalized_config):
    cluster_template.hadoop_version = normalized_config.hadoop_version
    for ng in normalized_config.node_groups:
        template_relation = m.TemplatesRelation(ng.name, ng.flavor,
                                                ng.node_processes,
                                                ng.count)
        cluster_template.node_groups.append(template_relation)
    for entry in normalized_config.cluster_configs:
        ci = entry.config
        # get the associated service dictionary
        service_dict = cluster_template.cluster_configs.get(
            entry.config.applicable_target, {})
        service_dict[ci.name] = entry.value
        cluster_template.cluster_configs[entry.config.applicable_target] = \
            service_dict

    LOG.debug('Cluster configs: {0}'.format(cluster_template.cluster_configs))

    return cluster_template
