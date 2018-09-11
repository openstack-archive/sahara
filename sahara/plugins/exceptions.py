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
from sahara.i18n import _


class NodeGroupCannotBeScaled(e.SaharaException):
    def __init__(self, ng_name, reason):
        self.message = _("Chosen node group %(ng_name)s cannot be scaled : "
                         "%(reason)s") % {"ng_name": ng_name, "reason": reason}
        self.code = "NODE_GROUP_CANNOT_BE_SCALED"
        super(NodeGroupCannotBeScaled, self).__init__()


class DecommissionError(e.SaharaException):
    code = "DECOMMISSION_ERROR"
    message = _("Failed to decommission cluster")

    def __init__(self, message=None):
        if message:
            self.message = message
        super(DecommissionError, self).__init__()


class ClusterCannotBeScaled(e.SaharaException):
    def __init__(self, cluster_name, reason):
        self.message = _("Cluster %(cluster_name)s cannot be scaled : "
                         "%(reason)s") % {"cluster_name": cluster_name,
                                          "reason": reason}
        self.code = "CLUSTER_CANNOT_BE_SCALED"
        super(ClusterCannotBeScaled, self).__init__()


class RequiredServiceMissingException(e.SaharaException):
    """Exception indicating that a required service has not been deployed."""

    def __init__(self, service_name, required_by=None):
        self.message = (_('Cluster is missing a service: %s')
                        % service_name)
        if required_by:
            self.message = (_('%(message)s, required by service: '
                              '%(required_by)s')
                            % {'message': self.message,
                               'required_by': required_by})

        self.code = 'MISSING_SERVICE'

        super(RequiredServiceMissingException, self).__init__()


class InvalidComponentCountException(e.SaharaException):
    """Exception indicating invalid number of components in a cluster.

    A message indicating a number of components cluster should contain and
    an invalid number of components are being deployed in a cluster.
    """

    def __init__(self, component, expected_count, count, description=None):
        message = _("Hadoop cluster should contain %(expected_count)s "
                    "%(component)s component(s)."
                    " Actual %(component)s count is %(count)s")

        if description:
            message = ("%(message)s. %(description)s"
                       % {'message': message, 'description': description})

        self.message = message % {"expected_count": expected_count,
                                  "component": component, "count": count}

        self.code = "INVALID_COMPONENT_COUNT"

        super(InvalidComponentCountException, self).__init__()


class InvalidClusterTopology(e.SaharaException):
    """Exception indicating another problems in a cluster topology,

    which is different from InvalidComponentCountException and
    RequiredServiceMissingException.
    """
    code = "INVALID_TOPOLOGY"
    message = _("Cluster has invalid topology: {description}")

    def __init__(self, description):
        self.message = self.message.format(description=description)
        super(InvalidClusterTopology, self).__init__()


class HadoopProvisionError(e.SaharaException):
    """Exception indicating that cluster provisioning failed.

    A message indicating the reason for failure must be provided.
    """

    base_message = _("Failed to Provision Hadoop Cluster: %s")

    def __init__(self, message):
        self.code = "HADOOP_PROVISION_FAILED"
        self.message = self.base_message % message

        super(HadoopProvisionError, self).__init__()


class NameNodeHAConfigurationError(e.SaharaException):
    """Exception indicating that hdp or cdh HDFS HA failed.

    A message indicating the reason for failure must be provided.
    """

    base_message = _("NameNode High Availability: %s")

    def __init__(self, message):
        self.code = "NAMENODE_HIGHAVAILABILITY_CONFIGURATION_FAILED"
        self.message = self.base_message % message

        super(NameNodeHAConfigurationError, self).__init__()


class ResourceManagerHAConfigurationError(e.SaharaException):
    """Exception indicating that cdh YARN HA failed.

    A message indicating the reason for failure must be provided.
    """

    base_message = _("ResourceManager High Availability: %s")

    def __init__(self, message):
        self.code = "RESOURCEMANAGER_HIGHAVAILABILITY_CONFIGURATION_FAILED"
        self.message = self.base_message % message

        super(ResourceManagerHAConfigurationError, self).__init__()


class ImageValidationSpecificationError(e.SaharaException):
    """Exception indicating that an image validation spec is in error."""

    base_message = _("Image validation spec is in error: %s")

    def __init__(self, message, *args):
        self.code = "IMAGE_SPECIFICATION_ERROR"
        self.message = self.base_message % message

        super(ImageValidationSpecificationError, self).__init__()


class ImageValidationError(e.SaharaException):
    """Exception indicating that an image has failed validation."""

    base_message = _("Image has failed validation: %s")

    def __init__(self, message):
        self.code = "IMAGE_VALIDATION_FAILED"
        self.message = self.base_message % message

        super(ImageValidationError, self).__init__()


class AllValidationsFailedError(ImageValidationError):
    """Exception indicating that all validations in an any block failed."""

    sub_message = _("All validations have failed: %s")

    def __init__(self, exceptions):
        data = ";".join(ex.message for ex in exceptions)
        message = self.sub_message % data

        super(AllValidationsFailedError, self).__init__(message)


class InvalidVolumeSizeException(e.SaharaException):
    """Exception indicating invalid configuration of components in a cluster.

    """

    def __init__(self, volume_size, reserved):
        message = _("Volume size: %(volume_size)s GB should be greater than "
                    "value of \"dfs_datanode_du_reserved\": %(reserved)s GB")
        self.message = message % {"volume_size": volume_size,
                                  "reserved": reserved}
        self.code = "INVALID_CONFIGURATION"

        super(InvalidVolumeSizeException, self).__init__()


class PluginInvalidDataException(e.InvalidDataException):

    code = "INVALID_DATA"
    message = _("Data is invalid")


class PluginConfigurationError(e.ConfigurationError):
    code = "CONFIGURATION_ERROR"
    message = _("The configuration has failed")


class PluginNotFoundException(e.NotFoundException):
    code = "NOT_FOUND"
    message_template = _("Object '%s' is not found")


class SaharaPluginException(e.SaharaException):
    code = "Sahara Plugin Exception"
    message = ""


class PluginRemoteCommandException(e.RemoteCommandException):
    code = "REMOTE_COMMAND_FAILED"
    message_template = _("Error during command execution: \"%s\"")
