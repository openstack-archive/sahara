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
        name=base.DATA_PROCESSING_JOB_BINARY % 'list',
        check_str=base.UNPROTECTED,
        description='List job binaries.',
        operations=[{'path': '/v2/job-binaries',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY % 'create',
        check_str=base.UNPROTECTED,
        description='Create job binary.',
        operations=[{'path': '/v2/job-binaries',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY % 'get-data',
        check_str=base.UNPROTECTED,
        description='Show job binary data.',
        operations=[
            {'path': '/v2/job-binaries/{job_binary_id}/data',
             'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY % 'update',
        check_str=base.UNPROTECTED,
        description='Update job binary.',
        operations=[
            {'path': '/v2/job-binaries/{job_binary_id}',
             'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY % 'get',
        check_str=base.UNPROTECTED,
        description='Show job binary details.',
        operations=[{'path': '/v2/job-binaries/{job_binary_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_BINARY % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete job binary.',
        operations=[{'path': '/v2/job-binaries/{job_binary_id}',
                     'method': 'DELETE'}]),
]


def list_rules():
    return job_binaries_policies
