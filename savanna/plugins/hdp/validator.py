# Copyright (c) 2013 Hortonworks, Inc.
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

import inspect

from savanna import conductor
from savanna import context
import savanna.exceptions as e
from savanna.plugins.general import exceptions as ex
from savanna.plugins.general import utils


conductor = conductor.API


class Validator(object):
    def validate(self, cluster):
        funcs = inspect.getmembers(Validator, predicate=inspect.ismethod)
        for func in funcs:
            if func[0].startswith("check_"):
                getattr(self, func[0])(cluster)

    def _get_named_node_group(self, cluster, ng_name):
        return next((ng for ng in cluster.node_groups
                     if ng.name == ng_name), None)

    def validate_scaling(self, cluster, existing, additional):
        orig_existing_count = {}
        ctx = context.ctx()
        try:
            for ng_id in existing:
                node_group = self._get_by_id(cluster.node_groups, ng_id)
                if node_group:
                    orig_existing_count[ng_id] = node_group.count
                    conductor.node_group_update(ctx, node_group,
                                                {'count':
                                                int(existing[ng_id])})
                else:
                    raise RuntimeError('Node group not found: {0}'.format(
                        ng_id
                    ))
            for ng_id in additional:
                node_group = self._get_by_id(cluster.node_groups, ng_id)
                if node_group:
                    conductor.node_group_update(ctx, node_group,
                                                {'count':
                                                int(additional[ng_id])})
                else:
                    raise RuntimeError('Node group not found: {0}'.format(
                        ng_id
                    ))

            self.validate(cluster)

        finally:
            for ng_id in additional:
                node_group = self._get_by_id(cluster.node_groups, ng_id)
                conductor.node_group_update(ctx, node_group,
                                            {'count': 0})
            for ng_id in orig_existing_count:
                node_group = self._get_by_id(cluster.node_groups, ng_id)
                conductor.node_group_update(ctx, node_group,
                                            {'count':
                                             orig_existing_count[ng_id]})

    def check_for_namenode(self, cluster):
        count = sum([ng.count for ng
                     in utils.get_node_groups(cluster, "NAMENODE")])
        if count != 1:
            raise ex.NotSingleNameNodeException(count)

    def check_for_jobtracker_and_tasktracker(self, cluster):
        jt_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "JOBTRACKER")])

        if jt_count not in [0, 1]:
            raise ex.NotSingleJobTrackerException(jt_count)

        tt_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "TASKTRACKER")])
        if jt_count is 0 and tt_count > 0:
            raise ex.TaskTrackersWithoutJobTracker()

    def check_for_ambari_server(self, cluster):
        count = sum([ng.count for ng
                     in utils.get_node_groups(cluster, "AMBARI_SERVER")])
        if count != 1:
            raise NotSingleAmbariServerException(count)

    def check_for_ambari_agents(self, cluster):
        for ng in cluster.node_groups:
            if "AMBARI_AGENT" not in ng.node_processes:
                raise AmbariAgentNumberException(ng.name)

    def _get_node_groups(self, node_groups, proc_list=list()):
        proc_list = [proc_list] if type(proc_list) in [str, unicode] \
            else proc_list
        return [ng for ng in node_groups
                if set(proc_list).issubset(ng.node_processes)]

    def _get_by_id(self, lst, id):
        for obj in lst:
            if obj.id == id:
                return obj

        return None


class NoNameNodeException(e.SavannaException):
    def __init__(self):
        self.message = ("Hadoop cluster should contain at least one namenode")
        self.code = "NO_NAMENODE"


class NotSingleAmbariServerException(e.SavannaException):
    def __init__(self, count):
        self.message = ("Hadoop cluster should contain 1 Ambari Server "
                        "instance. Actual Ambari server count is %s" % count)
        self.code = "NOT_SINGLE_AMBARI_SERVER"


class AmbariAgentNumberException(e.SavannaException):
    def __init__(self, count):
        self.message = ("Hadoop cluster should have an ambari agent per node "
                        "group. Node group %s has no Ambari Agent" % count)
        self.code = "WRONG_NUMBER_AMBARI_AGENTS"
