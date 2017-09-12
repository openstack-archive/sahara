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


data_sources_policies = [
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_DATA_SOURCES % 'get_all',
        check_str=base.UNPROTECTED,
        description='List data sources.',
        operations=[{'path': '/v1.1/{project_id}/data-sources',
                     'method': 'GET'},
                    {'path': '/v2/data-sources',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_DATA_SOURCES % 'get',
        check_str=base.UNPROTECTED,
        description='Show data source details.',
        operations=[
            {'path': '/v1.1/{project_id}/data-sources/{data_source_id}',
             'method': 'GET'},
            {'path': '/v2/data-sources/{data_source_id}',
             'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_DATA_SOURCES % 'register',
        check_str=base.UNPROTECTED,
        description='Create data source.',
        operations=[{'path': '/v1.1/{project_id}/data-sources',
                     'method': 'POST'},
                    {'path': '/v2/data-sources',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_DATA_SOURCES % 'modify',
        check_str=base.UNPROTECTED,
        description='Update data source.',
        operations=[
            {'path': '/v1.1/{project_id}/data-sources/{data_source_id}',
             'method': 'PUT'},
            {'path': '/v2/data-sources/{data_source_id}',
             'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.DATA_PROCESSING_DATA_SOURCES % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete data source.',
        operations=[
            {'path': '/v1.1/{project_id}/data-sources/{data_source_id}',
             'method': 'DELETE'},
            {'path': '/v2/data-sources/{data_source_id}',
             'method': 'DELETE'}]),
]


def list_rules():
    return data_sources_policies
