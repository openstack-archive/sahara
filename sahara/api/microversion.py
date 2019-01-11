#   Copyright 2018 OpenStack Contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

API_VERSIONS = ["2.0"]

MIN_API_VERSION = API_VERSIONS[0]
MAX_API_VERSION = API_VERSIONS[-1]

LATEST = "latest"
VERSION_STRING_REGEX = r"^([1-9]\d*).([1-9]\d*|0)$"

OPENSTACK_API_VERSION_HEADER = "OpenStack-API-Version"
VARY_HEADER = "Vary"
SAHARA_SERVICE_TYPE = "data-processing"

BAD_REQUEST_STATUS_CODE = 400
BAD_REQUEST_STATUS_NAME = "BAD_REQUEST"
NOT_ACCEPTABLE_STATUS_CODE = 406
NOT_ACCEPTABLE_STATUS_NAME = "NOT_ACCEPTABLE"
