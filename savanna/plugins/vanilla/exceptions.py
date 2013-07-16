# Copyright (c) 2013 Mirantis Inc.
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

import savanna.exceptions as e


class NotSingleNameNodeException(e.SavannaException):
    def __init__(self, nn_count):
        message = ("Hadoop cluster should contain only 1 NameNode "
                   "instance. Actual NN count is %s" % nn_count)
        code = "NOT_SINGLE_NAME_NODE"

        super(NotSingleNameNodeException, self).__init__(message, code)


class NotSingleJobTrackerException(e.SavannaException):
    def __init__(self, jt_count):
        message = ("Hadoop cluster should contain 0 or 1 JobTracker "
                   "instances. Actual JT count is %s" % jt_count)
        code = "NOT_SINGLE_JOB_TRACKER"

        super(NotSingleJobTrackerException, self).__init__(message, code)


class TaskTrackersWithoutJobTracker(e.SavannaException):
    def __init__(self):
        message = "TaskTrackers cannot be configures without JobTracker"
        code = "TASK_TRACKERS_WITHOUT_JOB_TRACKER"

        super(TaskTrackersWithoutJobTracker, self).__init__(message, code)


class NodeGroupsDoNotExist(e.SavannaException):
    def __init__(self, ng_names):
        names = ''.join(ng_names)
        message = "Cluster does not contain node groups: %s" % names
        code = "NODE_GROUP_DOES_NOT_EXIST"

        super(NodeGroupsDoNotExist, self).__init__(message, code)


class NodeGroupCannotBeScaled(e.SavannaException):
    def __init__(self, ng_name, reason):
        message = ("Chosen node group %s cannot be scaled : "
                   "%s" % (ng_name, reason))
        code = "NODE_GROUP_CANNOT_BE_SCALED"

        super(NodeGroupCannotBeScaled, self).__init__(message, code)
