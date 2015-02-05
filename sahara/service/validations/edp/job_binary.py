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

from oslo_config import cfg

import sahara.exceptions as e
import sahara.service.validations.edp.base as b
from sahara.swift import utils as su

CONF = cfg.CONF

JOB_BINARY_SCHEMA = {
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
        "url": {
            "type": "string",
            "format": "valid_job_location"
        },
        # extra is simple_config for now because we may need not only
        # user-password it the case of external storage
        "extra": {
            "type": "simple_config",
        }
    },
    "additionalProperties": False,
    "required": [
        "name",
        "url"
    ]
}


def check_job_binary(data, **kwargs):
    job_binary_location_type = data["url"]
    extra = data.get("extra", {})
    if job_binary_location_type.startswith(su.SWIFT_INTERNAL_PREFIX):
        if (not extra.get("user") or not extra.get("password")) and (
                not CONF.use_domain_for_proxy_users):
            raise e.BadJobBinaryException()
    if job_binary_location_type.startswith("internal-db"):
        internal_uid = job_binary_location_type[len("internal-db://"):]
        b.check_job_binary_internal_exists(internal_uid)
