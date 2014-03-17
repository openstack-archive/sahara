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

import six.moves.urllib.parse as urlparse

import sahara.exceptions as ex
import sahara.service.validations.edp.base as b


DATA_SOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 50,
            "format": "valid_name"
        },
        "description": {
            "type": "string"
        },
        "type": b.data_source_type,
        "url": {
            "type": "string",
        },
        "credentials": {
            "type": "object"
        }
    },
    "additionalProperties": False,
    "required": [
        "name",
        "type",
        "url"
    ]
}


def check_data_source_create(data, **kwargs):
    b.check_data_source_unique_name(data['name'])

    if "swift" == data["type"]:
        _check_swift_data_source_create(data)

    if "hdfs" == data["type"]:
        _check_hdfs_data_source_create(data)


def _check_swift_data_source_create(data):
    if "credentials" not in data or (
        not ("user" in data["credentials"] and
             "password" in data["credentials"])):
        raise ex.InvalidCredentials("Invalid credentials for Swift")


def _check_hdfs_data_source_create(data):
    if len(data['url']) == 0:
        raise ex.InvalidException("HDFS url must not be empty")
    url = urlparse.urlparse(data['url'])
    if url.scheme != "hdfs":
        raise ex.InvalidException("URL scheme must be 'hdfs'")
    if not url.hostname:
        raise ex.InvalidException("HDFS url is incorrect, "
                                  "cannot determine a hostname")
