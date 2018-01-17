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

from oslo_log import log as logging

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.service import api
from sahara.service.edp import job_manager as manager
from sahara.utils import edp
from sahara.utils import proxy as p


conductor = c.API
LOG = logging.getLogger(__name__)


def execute_job(data):
    # Elements common to all job types
    job_template_id = data['job_template_id']
    cluster_id = data['cluster_id']
    configs = data.get('job_configs', {})
    interface = data.get('interface', {})

    # Not in Java job types but present for all others
    input_id = data.get('input_id', None)
    output_id = data.get('output_id', None)

    # Since we will use a unified class in the database, we pass
    # a superset for all job types
    # example configs['start'] = '2015-05-12T08:55Z' frequency = 5 mins
    # the job will starts from 2015-05-12T08:55Z, runs every 5 mins

    job_execution_info = data.get('job_execution_info', {})

    configs['job_execution_info'] = job_execution_info

    job_ex_dict = {'input_id': input_id, 'output_id': output_id,
                   'job_id': job_template_id, 'cluster_id': cluster_id,
                   'info': {'status': edp.JOB_STATUS_PENDING},
                   'job_configs': configs, 'extra': {},
                   'interface': interface}
    job_execution = conductor.job_execution_create(context.ctx(), job_ex_dict)
    context.set_current_job_execution_id(job_execution.id)

    # check to use proxy user
    if p.job_execution_requires_proxy_user(job_execution):
        try:
            p.create_proxy_user_for_job_execution(job_execution)
        except ex.SaharaException as e:
            LOG.error("Can't run job execution. "
                      "(Reasons: {reason})".format(reason=e))
            conductor.job_execution_destroy(context.ctx(), job_execution)
            raise e

    api.OPS.run_edp_job(job_execution.id)

    return job_execution


def job_execution_list(**kwargs):
    return conductor.job_execution_get_all(context.ctx(),
                                           regex_search=True, **kwargs)


def get_job_execution(id, refresh_status=False):
    if refresh_status:
        return manager.get_job_status(id)
    else:
        return conductor.job_execution_get(context.ctx(), id)


def update_job_execution(id, values):
    _update_status(values.pop("info", None), id)
    return conductor.job_execution_update(context.ctx(), id, values)


def _update_status(info, id):
    if info:
        status = info.get("status", None)
        if status == edp.JOB_ACTION_SUSPEND:
            api.OPS.job_execution_suspend(id)
        if status == edp.JOB_ACTION_CANCEL:
            api.OPS.cancel_job_execution(id)


def delete_job_execution(id):
    context.set_current_job_execution_id(id)
    api.OPS.delete_job_execution(id)
