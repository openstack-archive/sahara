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

import itertools

from sahara.common.policies import base
from sahara.common.policies import cluster
from sahara.common.policies import cluster_template
from sahara.common.policies import cluster_templates
from sahara.common.policies import clusters
from sahara.common.policies import data_source
from sahara.common.policies import data_sources
from sahara.common.policies import image
from sahara.common.policies import images
from sahara.common.policies import job
from sahara.common.policies import job_binaries
from sahara.common.policies import job_binary
from sahara.common.policies import job_binary_internals
from sahara.common.policies import job_executions
from sahara.common.policies import job_template
from sahara.common.policies import job_type
from sahara.common.policies import job_types
from sahara.common.policies import jobs
from sahara.common.policies import node_group_template
from sahara.common.policies import node_group_templates
from sahara.common.policies import plugin
from sahara.common.policies import plugins


def list_rules():
    return itertools.chain(
        base.list_rules(),
        clusters.list_rules(),
        cluster_templates.list_rules(),
        data_sources.list_rules(),
        images.list_rules(),
        job_binaries.list_rules(),
        job_binary_internals.list_rules(),
        job_executions.list_rules(),
        job_types.list_rules(),
        jobs.list_rules(),
        node_group_templates.list_rules(),
        plugins.list_rules(),
        cluster.list_rules(),
        cluster_template.list_rules(),
        data_source.list_rules(),
        image.list_rules(),
        job_binary.list_rules(),
        job_type.list_rules(),
        job.list_rules(),
        node_group_template.list_rules(),
        plugin.list_rules(),
        job_template.list_rules()
    )
