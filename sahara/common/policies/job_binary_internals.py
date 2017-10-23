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


job_binary_internals_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY_INTERNALS % 'get',
        check_str=base.UNPROTECTED,
        description='Show job binary internal details.',
        operations=[{
            'path': '/v1.1/{project_id}/job-binary-internals/{job_bin_int_id}',
            'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY_INTERNALS % 'get_all',
        check_str=base.UNPROTECTED,
        description='List job binary internals.',
        operations=[{'path': '/v1.1/{project_id}/job-binary-internals',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY_INTERNALS % 'create',
        check_str=base.UNPROTECTED,
        description='Create job binary internals.',
        operations=[{'path': '/v1.1/{project_id}/job-binary-internals/{name}',
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY_INTERNALS % 'get_data',
        check_str=base.UNPROTECTED,
        description='Show job binary internal data.',
        operations=[{
            'path':
            '/v1.1/{project_id}/job-binary-internals/{job_bin_int_id}/data',
            'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY_INTERNALS % 'modify',
        check_str=base.UNPROTECTED,
        description='Update job binary internal.',
        operations=[{
            'path': '/v1.1/{project_id}/job-binary-internals/{job_bin_int_id}',
            'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY_INTERNALS % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete job binary internals.',
        operations=[{
            'path': '/v1.1/{project_id}/job-binary-internals/{job_bin_int_id}',
            'method': 'DELETE'}]),
]


def list_rules():
    return job_binary_internals_policies
