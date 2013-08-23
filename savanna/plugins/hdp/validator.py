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
import savanna.exceptions as e
from savanna.plugins.general import exceptions as ex
from savanna.plugins.general import utils


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
        try:
            for ng_name in existing:
                node_group = self._get_named_node_group(cluster, ng_name)
                if node_group:
                    orig_existing_count[ng_name] = node_group.count
                    node_group.count = int(existing[ng_name])
                else:
                    raise RuntimeError('Node group not found: {0}'.format(
                        ng_name
                    ))
            for node_group in additional:
                node_group.count = additional[node_group]
                cluster.node_groups.append(node_group)

            self.validate(cluster)

        finally:
            for node_group in additional:
                node_group.count = 0
                cluster.node_groups.remove(node_group)
            for ng_name in orig_existing_count:
                node_group = self._get_named_node_group(cluster, ng_name)
                node_group.count = orig_existing_count[ng_name]

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


class NoNameNodeException(e.SavannaException):
    def __init__(self):
        message = ("Hadoop cluster should contain at least one namenode")
        code = "NO_NAMENODE"

        super(NoNameNodeException, self).__init__(message, code)


class NotSingleAmbariServerException(e.SavannaException):
    def __init__(self, count):
        message = ("Hadoop cluster should contain 1 Ambari Server "
                   "instance. Actual Ambari server count is %s" % count)
        code = "NOT_SINGLE_AMBARI_SERVER"

        super(NotSingleAmbariServerException, self).__init__(message, code)


class AmbariAgentNumberException(e.SavannaException):
    def __init__(self, count):
        message = ("Hadoop cluster should have an ambari agent per "
                   "node group. Node group %s has no Ambari Agent" % count)
        code = "WRONG_NUMBER_AMBARI_AGENTS"

        super(AmbariAgentNumberException, self).__init__(message, code)
