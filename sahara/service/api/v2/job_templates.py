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
from sahara.service.edp import job_manager as manager


conductor = c.API


def get_job_templates(**kwargs):
    return conductor.job_get_all(context.ctx(), regex_search=True, **kwargs)


def get_job_template(id):
    return conductor.job_get(context.ctx(), id)


def create_job_template(values):
    return conductor.job_create(context.ctx(), values)


def update_job_template(id, values):
    return conductor.job_update(context.ctx(), id, values)


def delete_job_template(job_id):
    return conductor.job_destroy(context.ctx(), job_id)


def get_job_config_hints(job_type):
    return manager.get_job_config_hints(job_type)
