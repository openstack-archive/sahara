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


plugins_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_PLUGINS % 'get_all',
        check_str=base.UNPROTECTED,
        description='List plugins.',
        operations=[{'path': '/v1.1/{project_id}/plugins',
                     'method': 'GET'},
                    {'path': '/v2/plugins',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_PLUGINS % 'get_version',
        check_str=base.UNPROTECTED,
        description='Show plugins version details.',
        operations=[
            {'path': '/v1.1/{project_id}/plugins/{plugin_name}/{version}',
             'method': 'GET'},
            {'path': '/v2/plugins/{plugin_name}/{version}',
             'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_PLUGINS % 'get',
        check_str=base.UNPROTECTED,
        description='Show plugin details.',
        operations=[{'path': '/v1.1/{project_id}/plugins/{plugin_name}',
                     'method': 'GET'},
                    {'path': '/v2/plugins/{plugin_name}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_PLUGINS % 'convert_config',
        check_str=base.UNPROTECTED,
        description='Convert plugins to cluster template',
        operations=[
            {'path': ('/v1.1/{project_id}/plugins/{plugin_name}/'
                      '{version}/convert-config/{name}'),
             'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_PLUGINS % 'patch',
        check_str=base.ROLE_ADMIN,
        description='Update plugin details.',
        operations=[{'path': '/v1.1/{project_id}/plugins/{plugin_name}',
                     'method': 'PATCH'},
                    {'path': '/v2/plugins/{plugin_name}',
                     'method': 'PATCH'}]),
]


def list_rules():
    return plugins_policies
