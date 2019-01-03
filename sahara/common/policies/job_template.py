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


job_templates_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_TEMPLATE % 'get',
        check_str=base.UNPROTECTED,
        description='Show job template details.',
        operations=[{'path': '/v2/job-templates/{job_temp_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_TEMPLATE % 'create',
        check_str=base.UNPROTECTED,
        description='Create job templates.',
        operations=[{'path': '/v2/job-templates',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_TEMPLATE % 'list',
        check_str=base.UNPROTECTED,
        description='List job templates.',
        operations=[{'path': '/v2/job-templates',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_TEMPLATE % 'update',
        check_str=base.UNPROTECTED,
        description='Update job template.',
        operations=[{'path': '/v2/job-templates/{job_temp_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_TEMPLATE % 'get-config-hints',
        check_str=base.UNPROTECTED,
        description='Get job template config hints.',
        operations=[
            {'path': '/v2/job-templates/config-hints/{job_type}',
             'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_TEMPLATE % 'delete',
        check_str=base.UNPROTECTED,
        description='Remove job template.',
        operations=[{'path': '/v2/job-templates/{job_temp_id}',
                     'method': 'DELETE'}]),
]


def list_rules():
    return job_templates_policies
