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

import six

from sahara.i18n import _


class SaharaException(Exception):
    """Base Exception for the project

    To correctly use this class, inherit from it and define
    a 'message' and 'code' properties.
    """
    message = _("An unknown exception occurred")
    code = "UNKNOWN_EXCEPTION"

    def __str__(self):
        return self.message

    def __init__(self):
        super(SaharaException, self).__init__(
            '%s: %s' % (self.code, self.message))


class NotFoundException(SaharaException):
    message = _("Object '%s' is not found")
    # It could be a various property of object which was not found
    value = None

    def __init__(self, value, message=None):
        self.code = "NOT_FOUND"
        self.value = value
        if message:
            self.message = message % value


class NameAlreadyExistsException(SaharaException):
    message = _("Name already exists")

    def __init__(self, message=None):
        self.code = "NAME_ALREADY_EXISTS"
        if message:
            self.message = message


class InvalidCredentials(SaharaException):
    message = _("Invalid credentials")

    def __init__(self, message=None):
        self.code = "INVALID_CREDENTIALS"
        if message:
            self.message = message


class InvalidException(SaharaException):
    message = _("Invalid object reference")

    def __init__(self, message=None):
        self.code = "INVALID_REFERENCE"
        if message:
            self.message = message


class RemoteCommandException(SaharaException):
    message = _("Error during command execution: \"%s\"")

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


class InvalidDataException(SaharaException):
    """General exception to use for invalid data

    A more useful message should be passed to __init__ which
    tells the user more about why the data is invalid.
    """
    message = _("Data is invalid")
    code = "INVALID_DATA"

    def __init__(self, message=None):
        if message:
            self.message = message


class BadJobBinaryInternalException(SaharaException):
    message = _("Job binary internal data must be a string of length "
                "greater than zero")

    def __init__(self, message=None):
        if message:
            self.message = message
        self.code = "BAD_JOB_BINARY"


class BadJobBinaryException(SaharaException):
    message = _("To work with JobBinary located in internal swift add 'user'"
                " and 'password' to extra")

    def __init__(self, message=None):
        if message:
            self.message = message
        self.code = "BAD_JOB_BINARY"


class DBDuplicateEntry(SaharaException):
    message = _("Database object already exists")
    code = "DB_DUPLICATE_ENTRY"

    def __init__(self, message=None):
        if message:
            self.message = message


class CreationFailed(SaharaException):
    message = _("Object was not created")
    code = "CREATION_FAILED"

    def __init__(self, message=None):
        if message:
            self.message = message


class DeletionFailed(SaharaException):
    message = _("Object was not deleted")
    code = "DELETION_FAILED"

    def __init__(self, message=None):
        if message:
            self.message = message


class MissingFloatingNetworkException(SaharaException):
    def __init__(self, ng_name):
        self.message = _("Node Group %s is missing 'floating_ip_pool' "
                         "field") % ng_name
        self.code = "MISSING_FLOATING_NETWORK"


class SwiftClientException(SaharaException):
    '''General wrapper object for swift client exceptions

    This exception is intended for wrapping the message from a
    swiftclient.ClientException in a SaharaException. The ClientException
    should be caught and an instance of SwiftClientException raised instead.
    '''
    def __init__(self, message):
        self.message = message
        self.code = "SWIFT_CLIENT_EXCEPTION"


class DataTooBigException(SaharaException):
    message = _("Size of data (%(size)s) is greater than maximum "
                "(%(maximum)s)")

    def __init__(self, size, maximum, message=None):
        if message:
            self.message = message
        self.message = self.message % ({'size': size, 'maximum': maximum})
        self.code = "DATA_TOO_BIG"


class ThreadException(SaharaException):
    def __init__(self, thread_description, e):
        self.message = (_("An error occurred in thread '%(thread)s': %(e)s")
                        % {'thread': thread_description,
                           'e': six.text_type(e)})
        self.code = "THREAD_EXCEPTION"


class NotImplementedException(SaharaException):
    code = "NOT_IMPLEMENTED"

    def __init__(self, feature):
        self.message = _("Feature '%s' is not implemented") % feature


class HeatStackException(SaharaException):
    def __init__(self, heat_stack_status):
        self.code = "HEAT_STACK_EXCEPTION"
        self.message = (_("Heat stack failed with status %s") %
                        heat_stack_status)


class ConfigurationError(SaharaException):
    code = "CONFIGURATION_ERROR"

    def __init__(self, message):
        self.message = message


class IncorrectStateError(SaharaException):
    code = "INCORRECT_STATE_ERROR"

    def __init__(self, message):
        self.message = message


class SystemError(SaharaException):
    code = "SYSTEM_ERROR"

    def __init__(self, message):
        self.message = message


class EDPError(SaharaException):
    code = "EDP_ERROR"

    def __init__(self, message):
        self.message = message


class TimeoutException(SaharaException):
    code = "TIMEOUT"
    message = _("Operation timed out after %i second(s)")

    def __init__(self, timeout):
        self.message = self.message % timeout
