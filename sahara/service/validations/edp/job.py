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
from sahara.i18n import _
from sahara.service.api import v11 as api
from sahara.service.validations.edp import job_interface as j_i
from sahara.utils import edp


def _check_binaries(values):
    for job_binary in values:
        if not api.get_job_binary(job_binary):
            raise e.NotFoundException(job_binary,
                                      _("Job binary '%s' does not exist"))


def check_mains_libs(data, **kwargs):
    mains = data.get("mains", [])
    libs = data.get("libs", [])
    job_type, subtype = edp.split_job_type(data.get("type"))
    streaming = (job_type == edp.JOB_TYPE_MAPREDUCE and
                 subtype == edp.JOB_SUBTYPE_STREAMING)

    # These types must have a value in mains and may also use libs
    if job_type in [edp.JOB_TYPE_PIG, edp.JOB_TYPE_HIVE,
                    edp.JOB_TYPE_SHELL, edp.JOB_TYPE_SPARK,
                    edp.JOB_TYPE_STORM, edp.JOB_TYPE_PYLEUS]:
        if not mains:
            if job_type in [edp.JOB_TYPE_SPARK, edp.JOB_TYPE_STORM,
                            edp.JOB_TYPE_PYLEUS]:
                msg = _(
                    "%s job requires main application jar") % data.get("type")
            else:
                msg = _("%s flow requires main script") % data.get("type")
            raise e.InvalidDataException(msg)

        # Check for overlap
        if set(mains).intersection(set(libs)):
            raise e.InvalidDataException(_("'mains' and 'libs' overlap"))

    else:
        # Java and MapReduce require libs, but MapReduce.Streaming does not
        if not streaming and not libs:
            raise e.InvalidDataException(_("%s flow requires libs") %
                                         data.get("type"))
        if mains:
            raise e.InvalidDataException(_("%s flow does not use mains") %
                                         data.get("type"))

    # Make sure that all referenced binaries exist
    _check_binaries(mains)
    _check_binaries(libs)


def check_interface(data, **kwargs):
    j_i.check_job_interface(data, **kwargs)
