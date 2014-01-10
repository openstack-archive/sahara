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
        self.message = ("Hadoop cluster must contain exactly 1 NameNode "
                        "instance. Actual NN count is %s" % nn_count)
        self.code = "NOT_SINGLE_NAME_NODE"


class NotSingleJobTrackerException(e.SavannaException):
    def __init__(self, jt_count):
        self.message = ("Hadoop cluster must not contain more than 1 "
                        "JobTracker instance. Actual JT count is %s"
                        % jt_count)
        self.code = "NOT_SINGLE_JOB_TRACKER"


class OozieWithoutJobTracker(e.SavannaException):
    def __init__(self):
        self.message = "Oozie cannot be configured without JobTracker"
        self.code = "OOZIE_WITHOUT_JOB_TRACKER"


class NotSingleOozieException(e.SavannaException):
    def __init__(self, oozie_count):
        self.message = ("Cluster may contain only one Oozie server. "
                        "Requested Oozie's count is %s" % oozie_count)
        self.code = "NOT_SINGLE_OOZIE"


class TaskTrackersWithoutJobTracker(e.SavannaException):
    def __init__(self):
        self.message = "TaskTrackers cannot be configures without JobTracker"
        self.code = "TASK_TRACKERS_WITHOUT_JOB_TRACKER"


class NodeGroupsDoNotExist(e.SavannaException):
    def __init__(self, ng_names):
        names = ''.join(ng_names)
        self.message = "Cluster does not contain node groups: %s" % names
        self.code = "NODE_GROUP_DOES_NOT_EXIST"


class NodeGroupCannotBeScaled(e.SavannaException):
    def __init__(self, ng_name, reason):
        self.message = ("Chosen node group %s cannot be scaled : "
                        "%s" % (ng_name, reason))
        self.code = "NODE_GROUP_CANNOT_BE_SCALED"


class ClusterCannotBeScaled(e.SavannaException):
    def __init__(self, cluster_name, reason):
        self.message = ("Cluster %s cannot be scaled : "
                        "%s" % (cluster_name, reason))
        self.code = "CLUSTER_CANNOT_BE_SCALED"


class HiveWithoutJobTracker(e.SavannaException):
    def __init__(self):
        self.message = "Hive cannot be configured without JobTracker"
        self.code = "HIVE_WITHOUT_JOB_TRACKER"


class NotSingleHiveException(e.SavannaException):
    def __init__(self, h_count):
        self.message = ("Hadoop cluster should contain 0 or 1 Hive Server"
                        " instances. Actual Hive count is %s" % h_count)
        self.code = "NOT_SINGLE_HIVE"


class RequiredServiceMissingException(e.SavannaException):
    """A validation exception indicating that a required service
       has not been deployed
    """

    def __init__(self, service_name):
        self.message = 'Cluster is missing a required service: %s'\
                       % service_name
        self.code = 'MISSING_SERVICE'

        super(RequiredServiceMissingException, self).__init__()


class InvalidComponentCountException(e.SavannaException):
    """A validation exception indicating that an invalid number of
       components are being deployed in a cluster
    """

    def __init__(self, component, expected_count, count):
        self.message = ("Hadoop cluster should contain {0} {1} components."
                        " Actual {1} count is {2}".format(
                        expected_count, component, count))
        self.code = "INVALID_COMPONENT_COUNT"

        super(InvalidComponentCountException, self).__init__()


class HadoopProvisionError(e.SavannaException):
    """Exception indicating that cluster provisioning failed.

    A message indicating the reason for failure must be provided.
    """

    base_message = "Failed to Provision Hadoop Cluster: %s"

    def __init__(self, message):
        self.code = "HADOOP_PROVISION_FAILED"
        self.message = self.base_message % message

        super(HadoopProvisionError, self).__init__()
