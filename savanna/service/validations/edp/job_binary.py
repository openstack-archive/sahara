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

import savanna.exceptions as e


class BadJobBinaryException(e.SavannaException):
    message = "Job binary data must be a string of length greater than zero"

    def __init__(self):
        self.code = "BAD_JOB_BINARY"
        super(BadJobBinaryException, self).__init__(self.message, self.code)


def check_data_type_length(data, **kwargs):
    if not (type(data) is str and len(data) > 0):
        raise BadJobBinaryException()
