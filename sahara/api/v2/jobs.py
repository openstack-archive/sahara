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


@rest.get('/jobs')
@acl.enforce("data-processing:job-executions:get_all")
@v.check_exists(api.get_job_execution, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_job_executions)
def jobs_list():
    result = api.job_execution_list(**u.get_request_args().to_dict())
    # APIv2: renaming oozie_job_id -> engine_job_id
    # once APIv1 is deprecated this can be
    # removed
    for je in result:
        je['engine_job_id'] = je['oozie_job_id']
        del je['oozie_job_id']
    return u.render(res=result, name='jobs')


@rest.post('/jobs')
@acl.enforce("data-processing:job-executions:execute")
@v.validate(v_j_e_schema.JOB_EXEC_SCHEMA_V2, v_j_e.check_job_execution)
def jobs_execute(data):
    return u.render(api.execute_job(data).to_wrapped_dict())


@rest.get('/jobs/<job_id>')
@acl.enforce("data-processing:job-executions:get")
@v.check_exists(api.get_job_execution, id='job_id')
def jobs_get(job_id):
    data = u.get_request_args()
    refresh_status = six.text_type(
        data.get('refresh_status', 'false')).lower() == 'true'
    result = u.to_wrapped_dict_no_render(
        api.get_job_execution, job_id, refresh_status)
    result['engine_job_id'] = result['oozie_job_id']
    del result['oozie_job_id']
    return u.render(result)


@rest.get('/jobs/<job_id>/cancel')
@acl.enforce("data-processing:job-executions:cancel")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(None, v_j_e.check_job_execution_cancel)
def jobs_cancel(job_id):
    result = u.to_wrapped_dict_no_render(api.cancel_job_execution, job_id)
    result['engine_job_id'] = result['oozie_job_id']
    del result['oozie_job_id']
    return u.render(result)


@rest.patch('/jobs/<job_id>')
@acl.enforce("data-processing:job-executions:modify")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(
    v_j_e_schema.JOB_EXEC_UPDATE_SCHEMA, v_j_e.check_job_execution_update)
def jobs_update(job_id, data):
    result = u.to_wrapped_dict_no_render(
        api.update_job_execution, job_id, data)
    result['engine_job_id'] = result['oozie_job_id']
    del result['oozie_job_id']
    return u.render(result)


@rest.delete('/jobs/<job_id>')
@acl.enforce("data-processing:job-executions:delete")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(None, v_j_e.check_job_execution_delete)
def jobs_delete(job_id):
    api.delete_job_execution(job_id)
    return u.render()
