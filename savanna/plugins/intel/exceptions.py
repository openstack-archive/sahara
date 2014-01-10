# Copyright (c) 2013 Intel Corporation
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

import savanna.exceptions as e


class NotSingleManagerException(e.SavannaException):
    message = "Intel hadoop cluster should contain only 1 Intel " \
              "Manager instance. Actual manager count is %s"

    def __init__(self, mng_count):
        self.message = self.message % mng_count
        self.code = "NOT_SINGLE_MANAGER"


class IntelPluginException(e.SavannaException):
    def __init__(self, message):
        self.message = message
        self.code = "INTEL_PLUGIN_EXCEPTION"
