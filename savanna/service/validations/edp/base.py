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

import savanna.exceptions as ex
import savanna.service.edp.api as api

## Cluster creation related checks

data_source_type = {
    "type": "string",
    "enum": ["swift"]
}

job_type = {
    "type": "string",
    "enum": [
        "hive",
        "pig",
        "jar",
        "oozie"
    ]
}

job_storage = {
    "type": "string",
    "enum": [
        "swift",
        "hdfs",
        "internal"
    ]
}

user_pass = {
    "type": "object",
    "properties": {
        "user": {
            "type": "string",
        },
        "password": {
            "type": "string",
        }
    },
    "additionalProperties": False,
    "required": [
        "user",
        "password"
    ]
}


def check_data_source_unique_name(name):
    if name in [ds.name for ds in api.get_data_sources()]:
        raise ex.NameAlreadyExistsException("Data source with name '%s' "
                                            "already exists" % name)


def check_data_source_exists(data_source_id):
    if not api.get_data_source(data_source_id):
        raise ex.InvalidException("DataSource with id '%s'"
                                  " doesn't exist" % data_source_id)


def check_job_unique_name(name):
    if name in [j.name for j in api.get_jobs()]:
        raise ex.NameAlreadyExistsException("Job with name '%s' "
                                            "already exists" % name)


def check_job_binary_internal_exists(jbi_id):
    if not api.get_job_binary_internal(jbi_id):
        raise ex.InvalidException("JobBinaryInternal with id '%s'"
                                  " doesn't exist" % jbi_id)
