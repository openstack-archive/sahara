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
from savanna.service.edp import api


JOB_SCHEMA = {
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
        "type": {
            "type": "string",
            "enum": [
                "Pig",
                "Hive",
                "Jar",
            ],
        },
        "mains": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
            }
        },
        "libs": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
            }
        },
    },
    "additionalProperties": False,
    "required": [
        "name",
        "type",
    ]
}


def _check_binaries(values):
    for job_binary in values:
        if not api.get_job_binary(job_binary):
            raise e.NotFoundException(job_binary,
                                      "Job binary '%s' does not exist")


def check_mains_libs(data, **kwargs):
    mains = data.get("mains", [])
    libs = data.get("libs", [])

    # As a basic check, mains or libs has to be non-empty
    if not (mains or libs):
        raise e.InvalidDataException("'mains' or 'libs' must be non-empty")

    # Pig or Hive flow has to contain script in mains
    if data.get("type") in ['Pig', 'Hive'] and not mains:
        raise e.InvalidDataException("%s flow requires main script" %
                                     data.get("type"))

    # Check for overlap
    if set(mains).intersection(set(libs)):
        raise e.InvalidDataException("'mains' and 'libs' overlap")

    # Make sure that all referenced binaries exist
    _check_binaries(mains)
    _check_binaries(libs)
