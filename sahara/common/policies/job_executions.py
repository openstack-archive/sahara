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


job_executions_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_EXECUTIONS % 'get',
        check_str=base.UNPROTECTED,
        description='Show job executions details.',
        operations=[{'path': '/v1.1/{project_id}/job-executions/{job_exec_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_EXECUTIONS % 'modify',
        check_str=base.UNPROTECTED,
        description='Update job execution.',
        operations=[{'path': '/v1.1/{project_id}/job-executions/{job_exec_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_EXECUTIONS % 'get_all',
        check_str=base.UNPROTECTED,
        description='List job executions.',
        operations=[{'path': '/v1.1/{project_id}/job-executions',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_EXECUTIONS % 'refresh_status',
        check_str=base.UNPROTECTED,
        description='Refresh job execution status.',
        operations=[
            {'path':
             '/v1.1/{project_id}/job-executions/{job_exec_id}/refresh-status',
             'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_EXECUTIONS % 'cancel',
        check_str=base.UNPROTECTED,
        description='Cancel job execution.',
        operations=[{'path':
                     '/v1.1/{project_id}/job-executions/{job_exec_id}/cancel',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_EXECUTIONS % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete job execution.',
        operations=[{'path': '/v1.1/{project_id}/job-executions/{job_exec_id}',
                     'method': 'DELETE'}]),
]


def list_rules():
    return job_executions_policies
