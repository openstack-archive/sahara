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

from oslo_utils import uuidutils
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
        self.uuid = uuidutils.generate_uuid()
        self.message = (_('%(message)s\nError ID: %(id)s')
                        % {'message': self.message, 'id': self.uuid})


class NotFoundException(SaharaException):
    message = _("Object '%s' is not found")
    # It could be a various property of object which was not found
    value = None

    def __init__(self, value, message=None):
        self.code = "NOT_FOUND"
        self.value = value
        if message:
            self.message = message % value
        else:
            self.message = self.message % value
        super(NotFoundException, self).__init__()


class NameAlreadyExistsException(SaharaException):
    message = _("Name already exists")

    def __init__(self, message=None):
        self.code = "NAME_ALREADY_EXISTS"
        if message:
            self.message = message
        super(NameAlreadyExistsException, self).__init__()


class InvalidCredentials(SaharaException):
    message = _("Invalid credentials")

    def __init__(self, message=None):
        self.code = "INVALID_CREDENTIALS"
        if message:
            self.message = message
        super(InvalidCredentials, self).__init__()


class InvalidReferenceException(SaharaException):
    message = _("Invalid object reference")

    def __init__(self, message=None):
        self.code = "INVALID_REFERENCE"
        if message:
            self.message = message
        super(InvalidReferenceException, self).__init__()


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
            self.message = '%s\nReturn code: %s' % (self.message,
                                                    six.text_type(ret_code))

        if stderr:
            self.message = '%s\nSTDERR:\n%s' % (
                self.message, stderr.decode('ascii', 'ignore'))

        if stdout:
            self.message = '%s\nSTDOUT:\n%s' % (
                self.message, stdout.decode('ascii', 'ignore'))

        super(RemoteCommandException, self).__init__()


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
        super(InvalidDataException, self).__init__()


class BadJobBinaryInternalException(SaharaException):
    message = _("Job binary internal data must be a string of length "
                "greater than zero")

    def __init__(self, message=None):
        if message:
            self.message = message
        self.code = "BAD_JOB_BINARY"
        super(BadJobBinaryInternalException, self).__init__()


class BadJobBinaryException(SaharaException):
    message = _("To work with JobBinary located in internal swift add 'user'"
                " and 'password' to extra")

    def __init__(self, message=None):
        if message:
            self.message = message
        self.code = "BAD_JOB_BINARY"
        super(BadJobBinaryException, self).__init__()


class DBDuplicateEntry(SaharaException):
    message = _("Database object already exists")
    code = "DB_DUPLICATE_ENTRY"

    def __init__(self, message=None):
        if message:
            self.message = message
        super(DBDuplicateEntry, self).__init__()


class CreationFailed(SaharaException):
    message = _("Object was not created")
    code = "CREATION_FAILED"

    def __init__(self, message=None):
        if message:
            self.message = message
        super(CreationFailed, self).__init__()


class CancelingFailed(SaharaException):
    message = _("Operation was not canceled")
    code = "CANCELING_FAILED"

    def __init__(self, message=None):
        if message:
            self.message = message
        super(CancelingFailed, self).__init__()


class DeletionFailed(SaharaException):
    message = _("Object was not deleted")
    code = "DELETION_FAILED"

    def __init__(self, message=None):
        if message:
            self.message = message
        super(DeletionFailed, self).__init__()


class MissingFloatingNetworkException(SaharaException):
    def __init__(self, ng_name):
        self.message = _("Node Group %s is missing 'floating_ip_pool' "
                         "field") % ng_name
        self.code = "MISSING_FLOATING_NETWORK"
        super(MissingFloatingNetworkException, self).__init__()


class SwiftClientException(SaharaException):
    '''General wrapper object for swift client exceptions

    This exception is intended for wrapping the message from a
    swiftclient.ClientException in a SaharaException. The ClientException
    should be caught and an instance of SwiftClientException raised instead.
    '''
    def __init__(self, message):
        self.message = message
        self.code = "SWIFT_CLIENT_EXCEPTION"
        super(SwiftClientException, self).__init__()


class DataTooBigException(SaharaException):
    message = _("Size of data (%(size)s) is greater than maximum "
                "(%(maximum)s)")

    def __init__(self, size, maximum, message=None):
        if message:
            self.message = message
        self.message = self.message % ({'size': size, 'maximum': maximum})
        self.code = "DATA_TOO_BIG"
        super(DataTooBigException, self).__init__()


class ThreadException(SaharaException):
    def __init__(self, thread_description, e):
        self.message = (_("An error occurred in thread '%(thread)s': %(e)s")
                        % {'thread': thread_description,
                           'e': six.text_type(e)})
        self.code = "THREAD_EXCEPTION"
        super(ThreadException, self).__init__()


class NotImplementedException(SaharaException):
    code = "NOT_IMPLEMENTED"

    def __init__(self, feature):
        self.message = _("Feature '%s' is not implemented") % feature
        super(NotImplementedException, self).__init__()


class HeatStackException(SaharaException):
    def __init__(self, heat_stack_status):
        self.code = "HEAT_STACK_EXCEPTION"
        self.message = (_("Heat stack failed with status %s") %
                        heat_stack_status)
        super(HeatStackException, self).__init__()


class ConfigurationError(SaharaException):
    code = "CONFIGURATION_ERROR"

    def __init__(self, message):
        self.message = message
        super(ConfigurationError, self).__init__()


class IncorrectStateError(SaharaException):
    code = "INCORRECT_STATE_ERROR"

    def __init__(self, message):
        self.message = message
        super(IncorrectStateError, self).__init__()


class SystemError(SaharaException):
    code = "SYSTEM_ERROR"

    def __init__(self, message):
        self.message = message
        super(SystemError, self).__init__()


class EDPError(SaharaException):
    code = "EDP_ERROR"

    def __init__(self, message):
        self.message = message
        super(EDPError, self).__init__()


class TimeoutException(SaharaException):
    code = "TIMEOUT"
    message = _("'%(operation)s' timed out after %(timeout)i second(s)")

    def __init__(self, timeout, op_name=None, timeout_name=None):
        if op_name:
            op_name = _("Operation with name '%s'") % op_name
        else:
            op_name = _("Operation")
        self.message = self.message % {
            'operation': op_name, 'timeout': timeout}

        if timeout_name:
            desc = _("%(message)s and following timeout was violated: "
                     "%(timeout_name)s")
            self.message = desc % {
                'message': self.message, 'timeout_name': timeout_name}

        super(TimeoutException, self).__init__()


class DeprecatedException(SaharaException):
    code = "DEPRECATED"

    def __init__(self, message):
        self.message = message
        super(DeprecatedException, self).__init__()


class Forbidden(SaharaException):
    code = "FORBIDDEN"
    message = _("You are not authorized to complete this action.")

    def __init__(self, message=None):
        if message:
            self.message = message
        super(Forbidden, self).__init__()


class ImageNotRegistered(SaharaException):
    code = "IMAGE_NOT_REGISTERED"
    message = _("Image %s is not registered in Sahara")

    def __init__(self, image):
        self.message = self.message % image
        super(ImageNotRegistered, self).__init__()


class MalformedRequestBody(SaharaException):
    code = "MALFORMED_REQUEST_BODY"
    message = _("Malformed message body: %(reason)s")

    def __init__(self, reason):
        self.message = self.message % {"reason": reason}
        super(MalformedRequestBody, self).__init__()


class QuotaException(SaharaException):
    code = "QUOTA_ERROR"
    message = _("Quota exceeded for %(resource)s: Requested %(requested)s,"
                " but available %(available)s")

    def __init__(self, resource, requested, available):
        self.message = self.message % {'resource': resource,
                                       'requested': requested,
                                       'available': available}
        super(QuotaException, self).__init__()


class UpdateFailedException(SaharaException):
    message = _("Object '%s' could not be updated")
    # Object was unable to be updated

    def __init__(self, value, message=None):
        self.code = "UPDATE_FAILED"
        if message:
            self.message = message
        self.message = self.message % value
        super(UpdateFailedException, self).__init__()
