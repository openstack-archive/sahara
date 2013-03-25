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

from savanna.openstack.common.exception import ApiError


class SavannaException(ApiError):
    """
    Base Exception

    To correctly use this class, inherit from it and define
    a 'message' and 'code' properties.
    """
    message = "An unknown exception occurred"
    code = "UNKNOWN_EXCEPTION"

    def __str__(self):
        return self.message


## Cluster operations exceptions

class ClusterNameExistedException(SavannaException):
    def __init__(self, value):
        self.message = "Cluster with name '%s' already exists" % value
        self.code = "CLUSTER_NAME_ALREADY_EXISTS"


class ImageNotFoundException(SavannaException):
    def __init__(self, value):
        self.message = "Cannot find image with name '%s'" % value
        self.code = "IMAGE_NOT_FOUND"


class NotSingleNameNodeException(SavannaException):
    def __init__(self, nn_count):
        self.message = "Hadoop cluster should contain only 1 NameNode. " \
                       "Actual NN count is %s " % nn_count
        self.code = "NOT_SINGLE_NAME_NODE"


class NotSingleJobTrackerException(SavannaException):
    def __init__(self, jt_count):
        self.message = "Hadoop cluster should contain only 1 JobTracker. " \
                       "Actual JT count is %s " % jt_count
        self.code = "NOT_SINGLE_JOB_TRACKER"


## NodeTemplates operations exceptions

class NodeTemplateNotFoundException(SavannaException):
    def __init__(self, value):
        self.message = "Cannot find NodeTemplate '%s'" % value
        self.code = "NODE_TEMPLATE_NOT_FOUND"


class NodeTemplateExistedException(SavannaException):
    def __init__(self, value):
        self.message = "NodeTemplate with name '%s' already exists" % value
        self.code = "NODE_TEMPLATE_ALREADY_EXISTS"


class FlavorNotFoundException(SavannaException):
    def __init__(self, value):
        self.message = "Cannot find flavor with name '%s'" % value
        self.code = "FLAVOR_NOT_FOUND"


class DiscrepancyNodeProcessException(SavannaException):
    def __init__(self, value):
        self.message = "Discrepancies in Node Processes. Required: %s" % value
        self.code = "NODE_PROCESS_DISCREPANCY"


## NodeTypes operations exceptions

class NodeTypeNotFoundException(SavannaException):
    def __init__(self, value):
        self.message = "Cannot find NodeType '%s'" % value
        self.code = "NODE_TYPE_NOT_FOUND"
