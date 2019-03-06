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

import six

from sahara.api import acl
from sahara.service.api.v2 import jobs as api
from sahara.service import validation as v
from sahara.service.validations.edp import job_execution as v_j_e
from sahara.service.validations.edp import job_execution_schema as v_j_e_schema
import sahara.utils.api as u


rest = u.RestV2('jobs', __name__)


def _replace_job_id_job_template_id(job_obj):
    dict.update(job_obj, {'job_template_id': job_obj['job_id']})
    dict.pop(job_obj, 'job_id')


@rest.get('/jobs')
@acl.enforce("data-processing:job:list")
@v.check_exists(api.get_job_execution, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_job_executions)
@v.validate_request_params(['status'])
def jobs_list():
    result = api.job_execution_list(**u.get_request_args().to_dict())
    # APIv2: renaming oozie_job_id -> engine_job_id
    # once APIv1 is deprecated this can be
    # removed
    for je in result:
        je.pop('oozie_job_id', force=True)
        u._replace_tenant_id_project_id(je)
        _replace_job_id_job_template_id(je)
    return u.render(res=result, name='jobs')


@rest.post('/jobs')
@acl.enforce("data-processing:job:execute")
@v.validate(v_j_e_schema.JOB_EXEC_SCHEMA_V2, v_j_e.check_job_execution)
@v.validate_request_params([])
def jobs_execute(data):
    result = {'job': api.execute_job(data)}
    dict.update(result['job'],
                {'engine_job_id': result['job']['oozie_job_id']})
    dict.pop(result['job'], 'oozie_job_id')
    u._replace_tenant_id_project_id(result['job'])
    _replace_job_id_job_template_id(result['job'])
    return u.render(result)


@rest.get('/jobs/<job_id>')
@acl.enforce("data-processing:job:get")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate_request_params([])
def jobs_get(job_id):
    data = u.get_request_args()
    refresh_status = six.text_type(
        data.get('refresh_status', 'false')).lower() == 'true'
    result = {'job': api.get_job_execution(job_id, refresh_status)}
    result['job'].pop('oozie_job_id', force=True)
    u._replace_tenant_id_project_id(result['job'])
    _replace_job_id_job_template_id(result['job'])
    return u.render(result)


@rest.patch('/jobs/<job_id>')
@acl.enforce("data-processing:job:update")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(
    v_j_e_schema.JOB_EXEC_UPDATE_SCHEMA, v_j_e.check_job_execution_update)
@v.validate_request_params([])
def jobs_update(job_id, data):
    result = {'job': api.update_job_execution(job_id, data)}
    result['job'].pop('oozie_job_id', force=True)
    u._replace_tenant_id_project_id(result['job'])
    _replace_job_id_job_template_id(result['job'])
    return u.render(result)


@rest.delete('/jobs/<job_id>')
@acl.enforce("data-processing:job:delete")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(None, v_j_e.check_job_execution_delete)
@v.validate_request_params([])
def jobs_delete(job_id):
    api.delete_job_execution(job_id)
    return u.render()
