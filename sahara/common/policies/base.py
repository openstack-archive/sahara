# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_policy import policy

DATA_PROCESSING = 'data-processing:%s'
DATA_PROCESSING_CLUSTERS = DATA_PROCESSING % 'clusters:%s'
DATA_PROCESSING_CLUSTER_TEMPLATES = DATA_PROCESSING % 'cluster-templates:%s'
DATA_PROCESSING_DATA_SOURCES = DATA_PROCESSING % 'data-sources:%s'
DATA_PROCESSING_IMAGES = DATA_PROCESSING % 'images:%s'
DATA_PROCESSING_JOB_BINARIES = DATA_PROCESSING % 'job-binaries:%s'
DATA_PROCESSING_JOB_EXECUTIONS = DATA_PROCESSING % 'job-executions:%s'
DATA_PROCESSING_JOB_TYPES = DATA_PROCESSING % 'job-types:%s'
DATA_PROCESSING_JOBS = DATA_PROCESSING % 'jobs:%s'
DATA_PROCESSING_PLUGINS = DATA_PROCESSING % 'plugins:%s'
DATA_PROCESSING_NODE_GROUP_TEMPLATES = (
    DATA_PROCESSING % 'node-group-templates:%s')
DATA_PROCESSING_JOB_BINARY_INTERNALS = (
    DATA_PROCESSING % 'job-binary-internals:%s')

DATA_PROCESSING_CLUSTER = DATA_PROCESSING % 'cluster:%s'
DATA_PROCESSING_CLUSTER_TEMPLATE = DATA_PROCESSING % 'cluster-template:%s'
DATA_PROCESSING_DATA_SOURCE = DATA_PROCESSING % 'data-source:%s'
DATA_PROCESSING_IMAGE = DATA_PROCESSING % 'image:%s'
DATA_PROCESSING_JOB_BINARY = DATA_PROCESSING % 'job-binary:%s'
DATA_PROCESSING_JOB_TEMPLATE = DATA_PROCESSING % 'job-template:%s'
DATA_PROCESSING_JOB_TYPE = DATA_PROCESSING % 'job-type:%s'
DATA_PROCESSING_JOB = DATA_PROCESSING % 'job:%s'
DATA_PROCESSING_PLUGIN = DATA_PROCESSING % 'plugin:%s'
DATA_PROCESSING_NODE_GROUP_TEMPLATE = (
    DATA_PROCESSING % 'node-group-template:%s')
UNPROTECTED = ''
ROLE_ADMIN = 'role:admin'

rules = [
    policy.RuleDefault(
        name='context_is_admin',
        check_str=ROLE_ADMIN),
]


def list_rules():
    return rules
