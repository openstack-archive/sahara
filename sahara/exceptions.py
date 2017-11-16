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

import string

from oslo_utils import uuidutils
import six

from sahara.i18n import _


class SaharaException(Exception):
    """Base Exception for the project

    To correctly use this class, inherit from it and define
    a 'message' and 'code' properties.
    """
    code = "UNKNOWN_EXCEPTION"
    message = _("An unknown exception occurred")

    def __str__(self):
        return self.message

    def __init__(self, message=None, code=None, inject_error_id=True):
        self.uuid = uuidutils.generate_uuid()

        if code:
            self.code = code
        if message:
            self.message = message

        if inject_error_id:
            # Add Error UUID to the message if required
            self.message = (_('%(message)s\nError ID: %(id)s')
                            % {'message': self.message, 'id': self.uuid})

        super(SaharaException, self).__init__(
            '%s: %s' % (self.code, self.message))


class NotFoundException(SaharaException):
    code = "NOT_FOUND"
    message_template = _("Object '%s' is not found")

    # It could be a various property of object which was not found
    def __init__(self, value, message_template=None):
        self.value = value
        if message_template:
            formatted_message = message_template % value
        else:
            formatted_message = self.message_template % value

        super(NotFoundException, self).__init__(formatted_message)


class NoUniqueMatchException(SaharaException):
    code = "NO_UNIQUE_MATCH"
    message_template = _(
        "Response {response} is not unique for this query {query}.")

    def __init__(self, response, query, message_template=None):
        template = message_template or self.message_template
        formatted_message = template.format(response=response, query=query)
        super(NoUniqueMatchException, self).__init__(formatted_message)


class NameAlreadyExistsException(SaharaException):
    code = "NAME_ALREADY_EXISTS"
    message = _("Name already exists")


class InvalidCredentials(SaharaException):
    message = _("Invalid credentials")
    code = "INVALID_CREDENTIALS"


class InvalidReferenceException(SaharaException):
    code = "INVALID_REFERENCE"
    message = _("Invalid object reference")


class RemoteCommandException(SaharaException):
    code = "REMOTE_COMMAND_FAILED"
    message_template = _("Error during command execution: \"%s\"")

    def __init__(self, cmd, ret_code=None, stdout=None,
                 stderr=None):
        self.cmd = cmd
        self.ret_code = ret_code
        self.stdout = stdout
        self.stderr = stderr

        formatted_message = self.message_template % cmd

        def to_printable(s):
            return "".join(filter(lambda x: x in string.printable, s))

        if ret_code:
            formatted_message = '%s\nReturn code: %s' % (
                formatted_message, six.text_type(ret_code))

        if stderr:
            formatted_message = '%s\nSTDERR:\n%s' % (
                formatted_message, to_printable(stderr))

        if stdout:
            formatted_message = '%s\nSTDOUT:\n%s' % (
                formatted_message, to_printable(stdout))

        super(RemoteCommandException, self).__init__(formatted_message)


class InvalidDataException(SaharaException):
    """General exception to use for invalid data

    A more useful message should be passed to __init__ which
    tells the user more about why the data is invalid.
    """
    code = "INVALID_DATA"
    message = _("Data is invalid")


class BadJobBinaryInternalException(SaharaException):
    code = "BAD_JOB_BINARY"
    message = _("Job binary internal data must be a string of length "
                "greater than zero")


class BadJobBinaryException(SaharaException):
    code = "BAD_JOB_BINARY"
    message = _("To work with JobBinary located in internal swift add 'user'"
                " and 'password' to extra")


class DBDuplicateEntry(SaharaException):
    code = "DB_DUPLICATE_ENTRY"
    message = _("Database object already exists")


class CreationFailed(SaharaException):
    message = _("Object was not created")
    code = "CREATION_FAILED"


class CancelingFailed(SaharaException):
    message = _("Operation was not canceled")
    code = "CANCELING_FAILED"


class SuspendingFailed(SaharaException):
    message = _("Operation was not suspended")
    code = "SUSPENDING_FAILED"


class InvalidJobStatus(SaharaException):
    message = _("Invalid Job Status")
    code = "INVALID_JOB_STATUS"


class DeletionFailed(SaharaException):
    code = "DELETION_FAILED"
    message = _("Object was not deleted")


class MissingFloatingNetworkException(SaharaException):
    code = "MISSING_FLOATING_NETWORK"
    message_template = _("Node Group %s is missing 'floating_ip_pool' "
                         "field")

    def __init__(self, ng_name):
        formatted_message = self.message_template % ng_name

        super(MissingFloatingNetworkException, self).__init__(
            formatted_message)


class SwiftClientException(SaharaException):
    '''General wrapper object for swift client exceptions

    This exception is intended for wrapping the message from a
    swiftclient.ClientException in a SaharaException. The ClientException
    should be caught and an instance of SwiftClientException raised instead.
    '''

    code = "SWIFT_CLIENT_EXCEPTION"
    message = _("An error has occurred while performing a request to Swift")


class S3ClientException(SaharaException):
    '''General wrapper object for boto exceptions

    Intended to replace any errors raised by the botocore client.
    '''

    code = "S3_CLIENT_EXCEPTION"
    message = _("An error has occurred while performing a request to S3")


class DataTooBigException(SaharaException):
    code = "DATA_TOO_BIG"
    message_template = _("Size of data (%(size)s) is greater than maximum "
                         "(%(maximum)s)")

    def __init__(self, size, maximum, message_template=None):
        if message_template:
            self.message_template = message_template

        formatted_message = self.message_template % (
            {'size': size, 'maximum': maximum})

        super(DataTooBigException, self).__init__(formatted_message)


class ThreadException(SaharaException):
    code = "THREAD_EXCEPTION"
    message_template = _("An error occurred in thread '%(thread)s': %(e)s"
                         "\n%(stacktrace)s")

    def __init__(self, thread_description, e, stacktrace):
        formatted_message = self.message_template % {
            'thread': thread_description,
            'e': six.text_type(e),
            'stacktrace': stacktrace}

        super(ThreadException, self).__init__(formatted_message)


class SubprocessException(SaharaException):
    code = "SUBPROCESS_EXCEPTION"
    message = _("Subprocess execution has failed")


class NotImplementedException(SaharaException):
    code = "NOT_IMPLEMENTED"
    message_template = _("Feature '%s' is not implemented")

    def __init__(self, feature, message_template=None):
        if message_template:
            self.message_template = message_template

        formatted_message = self.message_template % feature

        super(NotImplementedException, self).__init__(formatted_message)


class HeatStackException(SaharaException):
    code = "HEAT_STACK_EXCEPTION"
    message_template = _("Heat stack failed with status %s")

    def __init__(self, heat_stack_status=None, message=None):
        if message:
            formatted_message = message
        elif heat_stack_status:
            formatted_message = self.message_template % heat_stack_status
        else:
            formatted_message = _("Heat stack failed")
        super(HeatStackException, self).__init__(formatted_message)


class ConfigurationError(SaharaException):
    code = "CONFIGURATION_ERROR"
    message = _("The configuration has failed")


class IncorrectStateError(SaharaException):
    message = _("The object is in an incorrect state")
    code = "INCORRECT_STATE_ERROR"


class FrozenClassError(SaharaException):
    code = "FROZEN_CLASS_ERROR"
    message_template = _("Class %s is immutable!")

    def __init__(self, instance):
        formatted_message = self.message_template % type(instance).__name__

        super(FrozenClassError, self).__init__(formatted_message)


class SystemError(SaharaException):
    code = "SYSTEM_ERROR"
    message = _("System error has occurred")


class EDPError(SaharaException):
    code = "EDP_ERROR"
    message = _("Failed to complete EDP operation")


class OozieException(SaharaException):
    code = "OOZIE_EXCEPTION"
    message = _("Failed to perform Oozie request")


class TimeoutException(SaharaException):
    code = "TIMEOUT"
    message_template = _("'%(operation)s' timed out after %(timeout)i "
                         "second(s)")

    def __init__(self, timeout, op_name=None, timeout_name=None):
        if op_name:
            op_name = _("Operation with name '%s'") % op_name
        else:
            op_name = _("Operation")
        formatted_message = self.message_template % {
            'operation': op_name, 'timeout': timeout}

        if timeout_name:
            desc = _("%(message)s and following timeout was violated: "
                     "%(timeout_name)s")
            formatted_message = desc % {
                'message': formatted_message, 'timeout_name': timeout_name}

        super(TimeoutException, self).__init__(formatted_message)


class DeprecatedException(SaharaException):
    code = "DEPRECATED"
    message = _("The version you are trying to use is deprecated")


class Forbidden(SaharaException):
    code = "FORBIDDEN"
    message = _("You are not authorized to complete this action")


class ImageNotRegistered(SaharaException):
    code = "IMAGE_NOT_REGISTERED"
    message_template = _("Image %s is not registered in Sahara")

    def __init__(self, image):
        formatted_message = self.message_template % image
        super(ImageNotRegistered, self).__init__(formatted_message)


class MalformedRequestBody(SaharaException):
    code = "MALFORMED_REQUEST_BODY"
    message_template = _("Malformed message body: %(reason)s")

    def __init__(self, reason):
        formatted_message = self.message_template % {"reason": reason}
        super(MalformedRequestBody, self).__init__(formatted_message)


class QuotaException(SaharaException):
    code = "QUOTA_ERROR"
    message_template = _("Quota exceeded for %(resource)s: "
                         "Requested %(requested)s, "
                         "but available %(available)s")

    def __init__(self, resource, requested, available):
        formatted_message = self.message_template % {
            'resource': resource,
            'requested': requested,
            'available': available}

        super(QuotaException, self).__init__(formatted_message)


class UpdateFailedException(SaharaException):
    code = "UPDATE_FAILED"
    message_template = _("Object '%s' could not be updated")
    # Object was unable to be updated

    def __init__(self, value, message_template=None):
        if message_template:
            self.message_template = message_template

        formatted_message = self.message_template % value

        super(UpdateFailedException, self).__init__(formatted_message)


class MaxRetriesExceeded(SaharaException):
    code = "MAX_RETRIES_EXCEEDED"
    message_template = _("Operation %(operation)s wasn't executed correctly "
                         "after %(attempts)d attempts")

    def __init__(self, attempts, operation):
        formatted_message = self.message_template % {'operation': operation,
                                                     'attempts': attempts}

        super(MaxRetriesExceeded, self).__init__(formatted_message)


class InvalidJobExecutionInfoException(SaharaException):
    message = _("Job execution information is invalid")

    def __init__(self, message=None):
        if message:
            self.message = message
        self.code = "INVALID_JOB_EXECUTION_INFO"
        super(InvalidJobExecutionInfoException, self).__init__()
