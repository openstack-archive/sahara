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
        name=base.DATA_PROCESSING_IMAGES % 'set_tags',
        check_str=base.UNPROTECTED,
        description='Add tags to image.',
        operations=[{'path': '/v2/images/{image_id}/tags',
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGES % 'add_tags',
        check_str=base.UNPROTECTED,
        description='Add tags to image.',
        operations=[{'path': '/v1.1/{project_id}/images/{image_id}/tag',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGES % 'register',
        check_str=base.UNPROTECTED,
        description='Register image.',
        operations=[{'path': '/v1.1/{project_id}/images/{image_id}',
                     'method': 'POST'},
                    {'path': '/v2/images/{image_id}',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGES % 'get_all',
        check_str=base.UNPROTECTED,
        description='List images.',
        operations=[{'path': '/v1.1/{project_id}/images', 'method': 'GET'},
                    {'path': '/v2/images', 'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGES % 'unregister',
        check_str=base.UNPROTECTED,
        description='Unregister image.',
        operations=[{'path': '/v1.1/{project_id}/images/{image_id}',
                     'method': 'POST'},
                    {'path': '/v2/images/{image_id}',
                     'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGES % 'get',
        check_str=base.UNPROTECTED,
        description='Show image details.',
        operations=[{'path': '/v1.1/{project_id}/images/{image_id}',
                     'method': 'GET'},
                    {'path': '/v2/images/{image_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_IMAGES % 'remove_tags',
        check_str=base.UNPROTECTED,
        description='Remove tags from image.',
        operations=[{'path': '/v1.1/{project_id}/images/{image_id}/untag',
                     'method': 'POST'},
                    {'path': '/v2/images/{image_id}/tags',
                     'method': 'DELETE'}]),
]


def list_rules():
    return images_policies
