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


node_group_templates_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_NODE_GROUP_TEMPLATE % 'list',
        check_str=base.UNPROTECTED,
        description='List node group templates.',
        operations=[{'path': '/v2/node-group-templates',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_NODE_GROUP_TEMPLATE % 'create',
        check_str=base.UNPROTECTED,
        description='Create node group template.',
        operations=[{'path': '/v2/node-group-templates',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_NODE_GROUP_TEMPLATE % 'get',
        check_str=base.UNPROTECTED,
        description='Show node group template details.',
        operations=[
            {'path': '/v2/node-group-templates/{node_group_temp_id}',
             'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_NODE_GROUP_TEMPLATE % 'update',
        check_str=base.UNPROTECTED,
        description='Update node group template.',
        operations=[
            {'path': '/v2/node-group-templates/{node_group_temp_id}',
             'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_NODE_GROUP_TEMPLATE % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete node group template.',
        operations=[
            {'path': '/v2/node-group-templates/{node_group_temp_id}',
             'method': 'DELETE'}]),
]


def list_rules():
    return node_group_templates_policies
