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


job_types_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_JOB_TYPE % 'list',
        check_str=base.UNPROTECTED,
        description='List job types.',
        operations=[{'path': '/v2/job-types',
                     'method': 'GET'}]),
]


def list_rules():
    return job_types_policies
