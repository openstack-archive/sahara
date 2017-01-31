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
from oslo_log import log as logging

import sahara.service.edp.job_binaries.manager as jb_manager

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def check_job_binary(data, **kwargs):
    job_binary_url = data.get("url", None)
    if job_binary_url:
        jb_manager.JOB_BINARIES.get_job_binary_by_url(job_binary_url). \
            validate(data, **kwargs)
