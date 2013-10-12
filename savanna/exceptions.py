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


class SavannaException(ex.Error):
    """Base Exception for the project

    To correctly use this class, inherit from it and define
    a 'message' and 'code' properties.
    """
    message = "An unknown exception occurred"
    code = "UNKNOWN_EXCEPTION"

    def __str__(self):
        return self.message

    def __init__(self):
        super(SavannaException, self).__init__(
            '%s: %s' % (self.code, self.message))


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


class BadJobBinaryInternalException(SavannaException):
    message = "Job binary internal data must be a string of length " \
              "greater than zero"

    def __init__(self, message=None):
        if message:
            self.message = message
        self.code = "BAD_JOB_BINARY"


class BadJobBinaryException(SavannaException):
    message = "To work with JobBinary located in internal swift add 'user'" \
              " and 'password' to extra"

    def __init__(self, message=None):
        if message:
            self.message = message
        self.code = "BAD_JOB_BINARY"


class DBDuplicateEntry(SavannaException):
    message = "Database object already exists"
    code = "DB_DUPLICATE_ENTRY"

    def __init__(self, message=None):
        if message:
            self.message = message


class DeletionFailed(SavannaException):
    message = "Object was not deleted"
    code = "DELETION_FAILED"

    def __init__(self, message=None):
        if message:
            self.message = message


class MissingFloatingNetworkException(SavannaException):
    def __init__(self, ng_name):
        self.message = ("Node Group %s is missing 'floating_ip_pool' "
                        "field" % ng_name)
        self.code = "MISSING_FLOATING_NETWORK"


class SwiftClientException(SavannaException):
    '''General wrapper object for swift client exceptions

    This exception is intended for wrapping the message from a
    swiftclient.ClientException in a SavannaException. The ClientException
    should be caught and an instance of SwiftClientException raised instead.
    '''
    def __init__(self, message):
        self.message = message
        self.code = "SWIFT_CLIENT_EXCEPTION"


class DataTooBigException(SavannaException):
    message = "Size of data (%s) is greater than maximum (%s)"

    def __init__(self, size, maximum, message=None):
        if message:
            self.message = message
        self.message = self.message % (size, maximum)
        self.code = "DATA_TOO_BIG"


class ThreadException(SavannaException):
    def __init__(self, thread_description, e):
        self.message = "An error occurred in thread '%s': %s" % (
            thread_description, str(e))
        self.code = "THREAD_EXCEPTION"
