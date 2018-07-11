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

"""Cluster creation related checks"""

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _

conductor = c.API

data_source_type = {
    "type": "string",
    "enum": ["swift", "hdfs", "maprfs", "manila", "s3"]
}

job_configs = {
    "type": "object",
    "properties": {
        "configs": {
            "type": "simple_config",
        },
        "params": {
            "type": "simple_config",
        },
        "args": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "job_execution_info": {
            "type": "simple_config",
        }
    },
    "additionalProperties": False,
}


def check_data_source_unique_name(ds_name):
    if ds_name in [ds.name for ds in
                   conductor.data_source_get_all(context.ctx(),
                                                 name=ds_name)]:
        raise ex.NameAlreadyExistsException(
            _("Data source with name '%s' "
              "already exists") % ds_name)


def check_data_source_exists(data_source_id):
    if not conductor.data_source_get(context.ctx(), data_source_id):
        raise ex.InvalidReferenceException(
            _("DataSource with id '%s' doesn't exist") % data_source_id)


def check_job_unique_name(job_name):
    if job_name in [job.name for job in
                    conductor.job_get_all(context.ctx(),
                                          name=job_name)]:
        raise ex.NameAlreadyExistsException(_("Job with name '%s' "
                                              "already exists") % job_name)


def check_job_binary_internal_exists(jbi_id):
    if not conductor.job_binary_internal_get(context.ctx(), jbi_id):
        raise ex.InvalidReferenceException(
            _("JobBinaryInternal with id '%s' doesn't exist") % jbi_id)


def check_data_sources_are_different(data_source_1_id, data_source_2_id):
    ds1 = conductor.data_source_get(context.ctx(), data_source_1_id)
    ds2 = conductor.data_source_get(context.ctx(), data_source_2_id)

    if ds1.type == ds2.type and ds1.url == ds2.url:
        raise ex.InvalidDataException(_('Provided input and output '
                                        'DataSources reference the same '
                                        'location: %s') % ds1.url)
