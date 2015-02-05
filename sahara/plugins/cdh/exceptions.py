# Copyright (c) 2015 Intel Corporation.
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

from sahara import exceptions as e
from sahara.i18n import _


class CMApiVersionError(e.SaharaException):
    """Exception indicating that CM API Version does not meet requirement.

    A message indicating the reason for failure must be provided.
    """

    base_message = _("CM API version not meet requirement: %s")

    def __init__(self, message):
        self.code = "CM_API_VERSION_ERROR"
        self.message = self.base_message % message

        super(CMApiVersionError, self).__init__()


class CMApiException(e.SaharaException):
    """Exception Type from CM API Errors.

    Any error result from the CM API is converted into this exception type.
    This handles errors from the HTTP level as well as the API level.
    """

    base_message = _("CM API error: %s")

    def __init__(self, message):
        self.code = "CM_API_EXCEPTION"
        self.message = self.base_message % message

        super(CMApiException, self).__init__()


class CMApiAttributeError(e.SaharaException):
    """Exception indicating a CM API attribute error.

    A message indicating the reason for failure must be provided.
    """

    base_message = _("CM API attribute error: %s")

    def __init__(self, message):
        self.code = "CM_API_ATTRIBUTE_ERROR"
        self.message = self.base_message % message

        super(CMApiAttributeError, self).__init__()


class CMApiValueError(e.SaharaException):
    """Exception indicating a CM API value error.

    A message indicating the reason for failure must be provided.
    """

    base_message = _("CM API value error: %s")

    def __init__(self, message):
        self.code = "CM_API_VALUE_ERROR"
        self.message = self.base_message % message

        super(CMApiValueError, self).__init__()
