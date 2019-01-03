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


clusters_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER % 'scale',
        check_str=base.UNPROTECTED,
        description='Scale cluster.',
        operations=[{'path': '/v2/clusters/{cluster_id}',
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER % 'list',
        check_str=base.UNPROTECTED,
        description='List available clusters',
        operations=[{'path': '/v2/clusters',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER % 'create',
        check_str=base.UNPROTECTED,
        description='Create cluster.',
        operations=[{'path': '/v2/clusters',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER % 'get',
        check_str=base.UNPROTECTED,
        description='Show details of a cluster.',
        operations=[{'path': '/v2/clusters/{cluster_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER % 'update',
        check_str=base.UNPROTECTED,
        description='Updates a cluster.',
        operations=[{'path': '/v2/clusters/{cluster_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_CLUSTER % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete a cluster.',
        operations=[{'path': '/v2/clusters/{cluster_id}',
                     'method': 'DELETE'}]),
]


def list_rules():
    return clusters_policies
