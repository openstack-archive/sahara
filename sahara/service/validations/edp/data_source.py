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

import re

from oslo_config import cfg

from sahara import conductor as c
from sahara import context
import sahara.exceptions as ex
from sahara.i18n import _
import sahara.service.edp.data_sources.manager as ds_manager
import sahara.service.validations.edp.base as b


CONF = cfg.CONF


def check_data_source_create(data, **kwargs):
    b.check_data_source_unique_name(data['name'])
    _check_data_source(data)


def _check_datasource_placeholder(url):
    if url is None:
        return
    total_length = 0
    substrings = re.findall(r"%RANDSTR\(([\-]?\d+)\)%", url)
    for length in map(int, substrings):
        if length <= 0:
            raise ex.InvalidDataException(_("Requested RANDSTR length"
                                            " must be positive."))
        total_length += length

    if total_length > 1024:
        raise ex.InvalidDataException(_("Requested RANDSTR length is"
                                        " too long, please choose a "
                                        "value less than 1024."))


def _check_data_source(data):
    _check_datasource_placeholder(data["url"])
    if data["type"] in CONF.data_source_types:
        ds_manager.DATA_SOURCES.get_data_source(data["type"]).validate(data)


def check_data_source_update(data, data_source_id):
    ctx = context.ctx()
    jobs = c.API.job_execution_get_all(ctx)
    pending_jobs = [job for job in jobs if job.info["status"] == "PENDING"]
    for job in pending_jobs:
        if data_source_id in job.data_source_urls:
            raise ex.UpdateFailedException(
                _("DataSource is used in a "
                  "PENDING Job and can not be updated."))

    ds = c.API.data_source_get(ctx, data_source_id)
    if 'name' in data and data['name'] != ds.name:
        b.check_data_source_unique_name(data['name'])

    check_data = {'type': data.get('type', None) or ds.type,
                  'url': data.get('url', None) or ds.url,
                  'credentials': data.get(
                      'credentials', None) or ds.credentials}
    _check_data_source(check_data)
