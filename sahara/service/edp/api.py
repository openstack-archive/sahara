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

from oslo.config import cfg
from oslo_log import log as logging

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _LE
from sahara.service.edp.binary_retrievers import dispatch
from sahara.service.edp import job_manager as manager
from sahara.utils import edp
from sahara.utils import proxy as p


conductor = c.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


OPS = None


def setup_edp_api(ops):
    global OPS

    OPS = ops


def get_job_config_hints(job_type):
    return manager.get_job_config_hints(job_type)


def execute_job(job_id, data):
    # Elements common to all job types
    cluster_id = data['cluster_id']
    configs = data.get('job_configs', {})

    # Not in Java job types but present for all others
    input_id = data.get('input_id', None)
    output_id = data.get('output_id', None)

    # Since we will use a unified class in the database, we pass
    # a superset for all job types
    job_ex_dict = {'input_id': input_id, 'output_id': output_id,
                   'job_id': job_id, 'cluster_id': cluster_id,
                   'info': {'status': edp.JOB_STATUS_PENDING},
                   'job_configs': configs, 'extra': {}}
    job_execution = conductor.job_execution_create(context.ctx(), job_ex_dict)

    # check to use proxy user
    if p.job_execution_requires_proxy_user(job_execution):
        try:
            p.create_proxy_user_for_job_execution(job_execution)
        except ex.SaharaException as e:
            LOG.exception(_LE("Can't run job execution '{0}' "
                              "(reasons: {1})").format(job_execution.id, e))
            conductor.job_execution_destroy(context.ctx(), job_execution)
            raise e

    OPS.run_edp_job(job_execution.id)

    return job_execution


def get_job_execution_status(id):
    return manager.get_job_status(id)


def job_execution_list(**kwargs):
    return conductor.job_execution_get_all(context.ctx(), **kwargs)


def get_job_execution(id):
    return conductor.job_execution_get(context.ctx(), id)


def cancel_job_execution(id):
    job_execution = conductor.job_execution_get(context.ctx(), id)
    OPS.cancel_job_execution(id)

    return job_execution


def delete_job_execution(id):
    OPS.delete_job_execution(id)


def get_data_sources(**kwargs):
    return conductor.data_source_get_all(context.ctx(), **kwargs)


def get_data_source(id):
    return conductor.data_source_get(context.ctx(), id)


def delete_data_source(id):
    conductor.data_source_destroy(context.ctx(), id)


def register_data_source(values):
    return conductor.data_source_create(context.ctx(), values)


def get_jobs(**kwargs):
    return conductor.job_get_all(context.ctx(), **kwargs)


def get_job(id):
    return conductor.job_get(context.ctx(), id)


def create_job(values):
    return conductor.job_create(context.ctx(), values)


def delete_job(job_id):
    return conductor.job_destroy(context.ctx(), job_id)


def create_job_binary(values):
    return conductor.job_binary_create(context.ctx(), values)


def get_job_binaries(**kwargs):
    return conductor.job_binary_get_all(context.ctx(), **kwargs)


def get_job_binary(id):
    return conductor.job_binary_get(context.ctx(), id)


def delete_job_binary(id):
    conductor.job_binary_destroy(context.ctx(), id)


def create_job_binary_internal(values):
    return conductor.job_binary_internal_create(context.ctx(), values)


def get_job_binary_internals(**kwargs):
    return conductor.job_binary_internal_get_all(context.ctx(), **kwargs)


def get_job_binary_internal(id):
    return conductor.job_binary_internal_get(context.ctx(), id)


def delete_job_binary_internal(id):
    conductor.job_binary_internal_destroy(context.ctx(), id)


def get_job_binary_internal_data(id):
    return conductor.job_binary_internal_get_raw_data(context.ctx(), id)


def get_job_binary_data(id):
    job_binary = conductor.job_binary_get(context.ctx(), id)
    return dispatch.get_raw_binary(job_binary, with_context=True)
