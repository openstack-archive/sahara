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

from oslo_policy import policy

from sahara.common.policies import base


cluster_templates_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER_TEMPLATE % 'create',
        check_str=base.UNPROTECTED,
        description='Create cluster template.',
        operations=[{'path': '/v2/cluster-templates',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER_TEMPLATE % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete a cluster template.',
        operations=[
            {'path': '/v2/cluster-templates/{cluster_temp_id}',
             'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER_TEMPLATE % 'update',
        check_str=base.UNPROTECTED,
        description='Update cluster template.',
        operations=[
            {'path': '/v2/cluster-templates/{cluster_temp_id}',
             'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER_TEMPLATE % 'get',
        check_str=base.UNPROTECTED,
        description='Show cluster template details.',
        operations=[
            {'path': '/v2/cluster-templates/{cluster_temp_id}',
             'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER_TEMPLATE % 'list',
        check_str=base.UNPROTECTED,
        description='List cluster templates.',
        operations=[{'path': '/v2/cluster-templates',
                     'method': 'GET'}]),
]


def list_rules():
    return cluster_templates_policies
