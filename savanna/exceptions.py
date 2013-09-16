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


class InvalidCredentials(SavannaException):
    def __init__(self, message=None):
        self.code = "INVALID_CREDENTIALS"
        if message:
            self.message = message


class InvalidException(SavannaException):
    message = "Invalid object reference"

    def __init__(self, message=None):
        self.code = "INVALID_REFERENCE"
        if message:
            self.message = message


class RemoteCommandException(SavannaException):
    message = "Error during command execution: \"%s\""

    def __init__(self, cmd, ret_code=None, stdout=None,
                 stderr=None):
        self.code = "REMOTE_COMMAND_FAILED"

        self.cmd = cmd
        self.ret_code = ret_code
        self.stdout = stdout
        self.stderr = stderr

        self.message = self.message % cmd

        if ret_code:
            self.message += '\nReturn code: ' + str(ret_code)

        if stderr:
            self.message += '\nSTDERR:\n' + stderr

        if stdout:
            self.message += '\nSTDOUT:\n' + stdout

        self.message = self.message.decode('ascii', 'ignore')


class InvalidDataException(SavannaException):
    """General exception to use for invalid data

    A more useful message should be passed to __init__ which
    tells the user more about why the data is invalid.
    """
    message = "Data is invalid"
    code = "INVALID_DATA"

    def __init__(self, message=None):
        if message:
            self.message = message

        super(InvalidDataException, self).__init__(self.message, self.code)


class BadJobBinaryInternalException(SavannaException):
    message = "Job binary internal data must be a string of length " \
              "greater than zero"

    def __init__(self):
        self.code = "BAD_JOB_BINARY"
        super(BadJobBinaryInternalException, self
              ).__init__(self.message, self.code)


class BadJobBinaryException(SavannaException):
    message = "To work with JobBinary located in internal swift add 'user'" \
              " and 'password' to extra"

    def __init__(self):
        self.code = "BAD_JOB_BINARY"
        super(BadJobBinaryException, self).__init__(self.message, self.code)


class DBDuplicateEntry(SavannaException):
    message = "Database object already exists"
    code = "DB_DUPLICATE_ENTRY"

    def __init__(self, message=None):
        if message:
            self.message = message
        super(DBDuplicateEntry, self).__init__(self.message, self.code)


class DeletionFailed(SavannaException):
    message = "Object was not deleted"
    code = "DELETION_FAILED"

    def __init__(self, message=None):
        if message:
            self.message = message
        super(DeletionFailed, self).__init__(self.message, self.code)
