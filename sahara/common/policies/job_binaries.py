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


job_binaries_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARIES % 'get_all',
        check_str=base.UNPROTECTED,
        description='List job binaries.',
        operations=[{'path': '/v1.1/{project_id}/job-binaries',
                     'method': 'GET'},
                    {'path': '/v2/job-binaries',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARIES % 'create',
        check_str=base.UNPROTECTED,
        description='Create job binary.',
        operations=[{'path': '/v1.1/{project_id}/job-binaries',
                     'method': 'POST'},
                    {'path': '/v2/job-binaries',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARIES % 'get_data',
        check_str=base.UNPROTECTED,
        description='Show job binary data.',
        operations=[
            {'path': '/v1.1/{project_id}/job-binaries/{job-binary_id}/data',
             'method': 'POST'},
            {'path': '/v2/job-binaries/{job-binary_id}/data',
             'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARIES % 'modify',
        check_str=base.UNPROTECTED,
        description='Update job binary.',
        operations=[
            {'path': '/v1.1/{project_id}/job-binaries/{job-binary_id}',
             'method': 'PUT'},
            {'path': '/v2/job-binaries/{job-binary_id}',
             'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARIES % 'get',
        check_str=base.UNPROTECTED,
        description='Show job binary details.',
        operations=[{'path': '/v1.1/{project_id}/job-binaries/{job_binary_id}',
                     'method': 'GET'},
                    {'path': '/v2/job-binaries/{job_binary_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARIES % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete job binary.',
        operations=[{'path': '/v1.1/{project_id}/job-binaries/{job_binary_id}',
                     'method': 'DELETE'},
                    {'path': '/v2/job-binaries/{job_binary_id}',
                     'method': 'DELETE'}]),
]


def list_rules():
    return job_binaries_policies
