# Copyright (c) 2015 Mirantis Inc.
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

from sahara import exceptions as exc
from sahara.tests.unit import base


class TestExceptions(base.SaharaTestCase):
    def _validate_exc(self, exc, expected_message, *args, **kwargs):
        message = ""
        try:
            raise exc(*args, **kwargs)
        except exc as e:
            message = six.text_type(e)
            if message.find("\nError ID") != -1:
                message = message.split("\nError ID")[0]

        self.assertEqual(expected_message, message)

    def test_not_found(self):
        self._validate_exc(
            exc.NotFoundException, "Object 'sample' is not found", "sample")
        self._validate_exc(
            exc.NotFoundException, "Not found 'sample'", "sample",
            "Not found '%s'")

    def test_name_already_exists(self):
        self._validate_exc(
            exc.NameAlreadyExistsException, "Name already exists")
        self._validate_exc(
            exc.NameAlreadyExistsException, "message", "message")

    def test_invalid_credentials(self):
        self._validate_exc(
            exc.InvalidCredentials, "Invalid credentials")
        self._validate_exc(
            exc.InvalidCredentials, "message", "message")

    def test_invalid_reference(self):
        self._validate_exc(
            exc.InvalidReferenceException, "Invalid object reference")
        self._validate_exc(
            exc.InvalidReferenceException, "message", "message")

    def test_remote_command(self):
        exc_message = ('Error during command execution: "cmd"\n'
                       'Return code: 0\n'
                       'STDERR:\n'
                       'stderr\n'
                       'STDOUT:\n'
                       'stdout')
        self._validate_exc(
            exc.RemoteCommandException, exc_message, "cmd", "0",
            "stdout", "stderr")

    def test_invalid_data(self):
        self._validate_exc(
            exc.InvalidDataException, "Data is invalid")
        self._validate_exc(
            exc.InvalidDataException, "message", "message")

    def test_bad_job_binary_internal(self):
        ex_message = ("Job binary internal data must be a string of length "
                      "greater than zero")
        self._validate_exc(
            exc.BadJobBinaryInternalException, ex_message)
        self._validate_exc(
            exc.BadJobBinaryInternalException, "message", "message")

    def test_bad_job_binary(self):
        ex_message = ("To work with JobBinary located in internal swift"
                      " add 'user' and 'password' to extra")
        self._validate_exc(
            exc.BadJobBinaryException, ex_message)
        self._validate_exc(
            exc.BadJobBinaryException, "message", "message")

    def test_db_duplicate(self):
        ex_message = "Database object already exists"
        self._validate_exc(
            exc.DBDuplicateEntry, ex_message)
        self._validate_exc(
            exc.DBDuplicateEntry, "message", "message")

    def test_creation_failed(self):
        ex_message = "Object was not created"
        self._validate_exc(
            exc.CreationFailed, ex_message)
        self._validate_exc(
            exc.CreationFailed, "message", "message")

    def test_canceling_failed(self):
        ex_message = "Operation was not canceled"
        self._validate_exc(
            exc.CancelingFailed, ex_message)
        self._validate_exc(
            exc.CancelingFailed, "message", "message")

    def test_deletion_failed(self):
        ex_message = "Object was not deleted"
        self._validate_exc(
            exc.DeletionFailed, ex_message)
        self._validate_exc(
            exc.DeletionFailed, "message", "message")

    def test_missing_floating_network(self):
        message = ("Node Group name is missing 'floating_ip_pool' "
                   "field")
        self._validate_exc(
            exc.MissingFloatingNetworkException, message, "name")

    def test_swift_client(self):
        self._validate_exc(exc.SwiftClientException, "message", "message")

    def test_data_too_big(self):
        exc_message = ("Size of data (size) is greater than maximum "
                       "(maximum)")
        self._validate_exc(
            exc.DataTooBigException, "size, maximum", "size", "maximum",
            "%(size)s, %(maximum)s")
        self._validate_exc(
            exc.DataTooBigException, exc_message, "size", "maximum")

    def test_not_implemented(self):
        self._validate_exc(
            exc.NotImplementedException, "Feature 'bond' is not implemented",
            "bond")
        self._validate_exc(
            exc.NotImplementedException, "feature", "feature", "%s")

    def test_incorrect_state(self):
        self._validate_exc(exc.IncorrectStateError, "message", "message")

    def test_deprecated(self):
        self._validate_exc(exc.DeprecatedException, "message", "message")

    def test_forbidden(self):
        self._validate_exc(exc.Forbidden, "message", "message")
        self._validate_exc(exc.Forbidden, "You are not authorized "
                                          "to complete this action")

    def test_image_not_registered(self):
        self._validate_exc(
            exc.ImageNotRegistered, 'Image image is not registered in Sahara',
            'image')

    def test_malformed_request_body(self):
        self._validate_exc(
            exc.MalformedRequestBody, "Malformed message body: reason",
            "reason")

    def test_update_failed(self):
        self._validate_exc(
            exc.UpdateFailedException, "Object 'value' could not be updated",
            "value")
        self._validate_exc(
            exc.UpdateFailedException, "value", "value", "%s")
