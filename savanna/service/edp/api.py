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


from savanna import conductor as c
from savanna import context
from savanna.openstack.common import log as logging

from savanna.service.edp import job_manager as manager


conductor = c.API
LOG = logging.getLogger(__name__)


def get_jobs():
    return conductor.job_get_all(context.ctx())


def get_job(id):
    return conductor.job_get(context.ctx(), id)


def create_job(values):
    return conductor.job_create(context.ctx(), values)


def delete_job(id):
    conductor.job_destroy(context.ctx(), id)


def execute_job(job_id, input_id, output_id, cluster_id, data):
    job_ex_dict = {'input_id': input_id, 'output_id': output_id,
                   'job_id': job_id, 'cluster_id': cluster_id,
                   'info': {'status': 'Pending'}}
    job_execution = conductor.job_execution_create(context.ctx(), job_ex_dict)
    return manager.run_job(context.ctx(), job_execution)


def get_job_execution_status(id):
    return manager.get_job_status(id)


def job_execution_list():
    return conductor.job_execution_get_all(context.ctx())


def get_job_execution(id):
    return conductor.job_execution_get(context.ctx(), id)


def cancel_job_execution(id):
    return manager.cancel_job(id)


def delete_job_execution(id):
    conductor.job_execution_destroy(context.ctx(), id)


def get_data_sources():
    return conductor.data_source_get_all(context.ctx())


def get_data_source(id):
    return conductor.data_source_get(context.ctx(), id)


def delete_data_source(id):
    conductor.data_source_destroy(context.ctx(), id)


def register_data_source(values):
    return conductor.data_source_create(context.ctx(), values)


def get_job_origins():
    return conductor.job_origin_get_all(context.ctx())


def get_job_origin(id):
    return conductor.job_origin_get(context.ctx(), id)


def create_job_origin(values):
    return conductor.job_origin_create(context.ctx(), values)


def delete_job_origin(job_origin_id):
    return conductor.job_origin_destroy(context.ctx(), job_origin_id)


def create_job_binary(values):
    return conductor.job_binary_create(context.ctx(), values)


def get_job_binaries():
    return conductor.job_binary_get_all(context.ctx())


def get_job_binary(id):
    return conductor.job_binary_get(context.ctx(), id)


def delete_job_binary(id):
    conductor.job_binary_destroy(context.ctx(), id)


def get_job_binary_data(id):
    return conductor.job_binary_get_raw_data(context.ctx(), id)
