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
import six

import sahara.exceptions as e
from sahara.i18n import _
from sahara.service.edp.job_binaries import manager as jb_manager
from sahara.utils import api_validator as a

CONF = cfg.CONF


def is_internal_db_enabled():
    return 'internal-db' in jb_manager.JOB_BINARIES.get_job_binaries()


def check_job_binary_internal(data, **kwargs):
    if not is_internal_db_enabled():
        raise e.BadJobBinaryInternalException(
            _("Sahara internal db is disabled for storing job binaries."))
    if not (isinstance(data, six.binary_type) and len(data) > 0):
        raise e.BadJobBinaryInternalException()
    if "name" in kwargs:
        name = kwargs["name"]
        if not a.validate_name_format(name):
            raise e.BadJobBinaryInternalException(_("%s is not a valid name")
                                                  % name)
