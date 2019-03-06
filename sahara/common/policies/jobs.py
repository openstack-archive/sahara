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


jobs_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOBS % 'execute',
        check_str=base.UNPROTECTED,
        description='Run job.',
        operations=[{'path': '/v1.1/{project_id}/jobs/{job_id}/execute',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOBS % 'get',
        check_str=base.UNPROTECTED,
        description='Show job details.',
        operations=[{'path': '/v1.1/{project_id}/jobs/{job_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOBS % 'create',
        check_str=base.UNPROTECTED,
        description='Create job.',
        operations=[{'path': '/v1.1/{project_id}/jobs', 'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOBS % 'get_all',
        check_str=base.UNPROTECTED,
        description='List jobs.',
        operations=[{'path': '/v1.1/{project_id}/jobs', 'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOBS % 'modify',
        check_str=base.UNPROTECTED,
        description='Update job object.',
        operations=[{'path': '/v1.1/{project_id}/jobs/{job_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOBS % 'get_config_hints',
        check_str=base.UNPROTECTED,
        description='Get job config hints.',
        operations=[
            {'path': '/v1.1/{project_id}/jobs/get_config_hints/{job_type}',
             'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOBS % 'delete',
        check_str=base.UNPROTECTED,
        description='Remove job.',
        operations=[{'path': '/v1.1/{project_id}/jobs/{job_id}',
                     'method': 'DELETE'}]),
]


def list_rules():
    return jobs_policies
