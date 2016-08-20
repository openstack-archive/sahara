# Copyright (c) 2014 Mirantis Inc.
#
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

import re

from oslo_log import log as logging

from sahara import conductor as cond
from sahara import context
from sahara.i18n import _LW
from sahara.plugins.vanilla import utils as u
from sahara.service.castellan import utils as castellan

conductor = cond.API

LOG = logging.getLogger(__name__)


def get_datanodes_status(cluster):
    statuses = {}
    namenode = u.get_namenode(cluster)
    status_regexp = r'^Hostname: (.*)\nDecommission Status : (.*)$'
    matcher = re.compile(status_regexp, re.MULTILINE)
    dfs_report = namenode.remote().execute_command(
        'sudo su - -c "hdfs dfsadmin -report" hadoop')[1]

    for host, status in matcher.findall(dfs_report):
        statuses[host] = status.lower()

    return statuses


def get_nodemanagers_status(cluster):
    statuses = {}
    resourcemanager = u.get_resourcemanager(cluster)
    status_regexp = r'^(\S+):\d+\s+(\w+)'
    matcher = re.compile(status_regexp, re.MULTILINE)
    yarn_report = resourcemanager.remote().execute_command(
        'sudo su - -c "yarn node -all -list" hadoop')[1]

    for host, status in matcher.findall(yarn_report):
        statuses[host] = status.lower()

    return statuses


def get_oozie_password(cluster):
    cluster = conductor.cluster_get(context.ctx(), cluster)
    extra = cluster.extra.to_dict()
    if 'oozie_pass_id' not in extra:
        extra['oozie_pass_id'] = u.generate_random_password()
        conductor.cluster_update(context.ctx(), cluster, {'extra': extra})
    return castellan.get_secret(extra['oozie_pass_id'])


def delete_oozie_password(cluster):
    extra = cluster.extra.to_dict()
    if 'oozie_pass_id' in extra:
        castellan.delete_secret(extra['oozie_pass_id'])
    else:
        LOG.warning(_LW("Cluster hasn't Oozie password"))


def get_hive_password(cluster):
    cluster = conductor.cluster_get(context.ctx(), cluster)
    extra = cluster.extra.to_dict()
    if 'hive_pass_id' not in extra:
        extra['hive_pass_id'] = u.generate_random_password()
        conductor.cluster_update(context.ctx(), cluster, {'extra': extra})
    return castellan.get_secret(extra['hive_pass_id'])


def delete_hive_password(cluster):
    extra = cluster.extra.to_dict()
    if 'hive_pass_id' in extra:
        castellan.delete_secret(extra['hive_pass_id'])
    else:
        LOG.warning(_LW("Cluster hasn't hive password"))
