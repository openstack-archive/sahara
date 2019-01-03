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


images_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGE % 'set-tags',
        check_str=base.UNPROTECTED,
        description='Add tags to image.',
        operations=[{'path': '/v2/images/{image_id}/tags',
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGE % 'register',
        check_str=base.UNPROTECTED,
        description='Register image.',
        operations=[{'path': '/v2/images/{image_id}',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGE % 'list',
        check_str=base.UNPROTECTED,
        description='List images.',
        operations=[{'path': '/v2/images', 'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGE % 'unregister',
        check_str=base.UNPROTECTED,
        description='Unregister image.',
        operations=[{'path': '/v2/images/{image_id}',
                     'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGE % 'get',
        check_str=base.UNPROTECTED,
        description='Show image details.',
        operations=[{'path': '/v2/images/{image_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGE % 'remove-tags',
        check_str=base.UNPROTECTED,
        description='Remove tags from image.',
        operations=[{'path': '/v2/images/{image_id}/tags',
                     'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGE % 'get-tags',
        check_str=base.UNPROTECTED,
        description='List tags on an image.',
        operations=[{'path': '/v2/images/{image_id}/tags',
                     'method': 'GET'}]),
]


def list_rules():
    return images_policies
