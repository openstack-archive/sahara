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

import sahara.exceptions as e


class NodeGroupCannotBeScaled(e.SaharaException):
    def __init__(self, ng_name, reason):
        self.message = ("Chosen node group %s cannot be scaled : "
                        "%s" % (ng_name, reason))
        self.code = "NODE_GROUP_CANNOT_BE_SCALED"


class DecommissionError(e.SaharaException):
    code = "DECOMMISSION_ERROR"
    message = "Failed to decommission cluster"

    def __init__(self, message):
        if message:
            self.message = message


class ClusterCannotBeScaled(e.SaharaException):
    def __init__(self, cluster_name, reason):
        self.message = ("Cluster %s cannot be scaled : "
                        "%s" % (cluster_name, reason))
        self.code = "CLUSTER_CANNOT_BE_SCALED"


class RequiredServiceMissingException(e.SaharaException):
    """Exception indicating that a required service has not been deployed."""

    def __init__(self, service_name, required_by=None):
        self.message = ('Cluster is missing a service: %s'
                        % service_name)
        if required_by:
            self.message = ('%s, required by service: %s'
                            % (self.message, required_by))

        self.code = 'MISSING_SERVICE'

        super(RequiredServiceMissingException, self).__init__()


class InvalidComponentCountException(e.SaharaException):
    """Exception indicating invalid number of components in a cluster.

    A message indicating a number of components cluster should contain and
    an invalid number of components are being deployed in a cluster.
    """

    def __init__(self, component, expected_count, count, description=None):
        self.message = ("Hadoop cluster should contain {0} {1} component(s)."
                        " Actual {1} count is {2}".format(
                            expected_count, component, count))
        if description:
            self.message += '. ' + description
        self.code = "INVALID_COMPONENT_COUNT"

        super(InvalidComponentCountException, self).__init__()


class HadoopProvisionError(e.SaharaException):
    """Exception indicating that cluster provisioning failed.

    A message indicating the reason for failure must be provided.
    """

    base_message = "Failed to Provision Hadoop Cluster: %s"

    def __init__(self, message):
        self.code = "HADOOP_PROVISION_FAILED"
        self.message = self.base_message % message

        super(HadoopProvisionError, self).__init__()
