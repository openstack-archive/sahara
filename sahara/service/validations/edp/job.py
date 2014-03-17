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

import sahara.exceptions as e
from sahara.service.edp import api
from sahara.utils import edp

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
                "MapReduce",
                "MapReduce.Streaming",
                "Java"
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
        "streaming": {
            "type": "boolean"
        }
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
    job_type, subtype = edp.split_job_type(data.get("type"))
    streaming = job_type == "MapReduce" and subtype == "Streaming"

    # Pig or Hive flow has to contain script in mains, may also use libs
    if job_type in ['Pig', 'Hive']:
        if not mains:
            raise e.InvalidDataException("%s flow requires main script" %
                                         data.get("type"))
        # Check for overlap
        if set(mains).intersection(set(libs)):
            raise e.InvalidDataException("'mains' and 'libs' overlap")

    else:
        if not streaming and not libs:
            raise e.InvalidDataException("%s flow requires libs" %
                                         data.get("type"))
        if mains:
            raise e.InvalidDataException("%s flow does not use mains" %
                                         data.get("type"))

    # Make sure that all referenced binaries exist
    _check_binaries(mains)
    _check_binaries(libs)
