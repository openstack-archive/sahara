# Copyright (c) 2016 Red Hat, Inc.
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

from sahara import conductor as c
from sahara import context
from sahara.service.edp.job_binaries import manager as jb_manager

conductor = c.API


def create_job_binary(values):
    return conductor.job_binary_create(context.ctx(), values)


def get_job_binaries(**kwargs):
    return conductor.job_binary_get_all(context.ctx(),
                                        regex_search=True, **kwargs)


def get_job_binary(id):
    return conductor.job_binary_get(context.ctx(), id)


def update_job_binary(id, values):
    return conductor.job_binary_update(context.ctx(), id, values)


def delete_job_binary(id):
    conductor.job_binary_destroy(context.ctx(), id)


def get_job_binary_data(id):
    job_binary = conductor.job_binary_get(context.ctx(), id)
    return jb_manager.JOB_BINARIES.get_job_binary(job_binary.type). \
        get_raw_data(job_binary, with_context=True)
