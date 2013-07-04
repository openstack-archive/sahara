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

import savanna.openstack.common.exception as ex


class SavannaException(ex.ApiError):
    """Base Exception for the project

    To correctly use this class, inherit from it and define
    a 'message' and 'code' properties.
    """
    message = "An unknown exception occurred"
    code = "UNKNOWN_EXCEPTION"

    def __str__(self):
        return self.message


class NotFoundException(SavannaException):

    message = "Object not found"
    # It could be a various property of object which was not found
    value = None

    def __init__(self, value, message=None):
        self.code = "NOT_FOUND"
        self.value = value
        if message:
            self.message = message % value


class NameAlreadyExistsException(SavannaException):

    message = "Name already exists"

    def __init__(self, message=None):
        self.code = "NAME_ALREADY_EXISTS"
        if message:
            self.message = message


class InvalidException(SavannaException):

    message = "Invalid object reference"

    def __init__(self, message=None):
        self.code = "INVALID_REFERENCE"
        if message:
            self.message = message
