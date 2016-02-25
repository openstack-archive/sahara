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


from sahara.api import acl
from sahara.service.edp import api
from sahara.service import validation as v
from sahara.service.validations.edp import job_execution as v_j_e
from sahara.service.validations.edp import job_execution_schema as v_j_e_schema
import sahara.utils.api as u


rest = u.RestV2('job-executions', __name__)


@rest.get('/job-executions')
@acl.enforce("data-processing:job-executions:get_all")
def job_executions_list():
    job_executions = [je.to_dict() for je in api.job_execution_list(
        **u.get_request_args().to_dict())]
    return u.render(job_executions=job_executions)


@rest.get('/job-executions/<job_execution_id>')
@acl.enforce("data-processing:job-executions:get")
@v.check_exists(api.get_job_execution, id='job_execution_id')
def job_executions(job_execution_id):
    return u.to_wrapped_dict(api.get_job_execution, job_execution_id)


@rest.get('/job-executions/<job_execution_id>/refresh-status')
@acl.enforce("data-processing:job-executions:refresh_status")
@v.check_exists(api.get_job_execution, id='job_execution_id')
def job_executions_status(job_execution_id):
    return u.to_wrapped_dict(
        api.get_job_execution_status, job_execution_id)


@rest.get('/job-executions/<job_execution_id>/cancel')
@acl.enforce("data-processing:job-executions:cancel")
@v.check_exists(api.get_job_execution, id='job_execution_id')
@v.validate(None, v_j_e.check_job_execution_cancel)
def job_executions_cancel(job_execution_id):
    return u.to_wrapped_dict(api.cancel_job_execution, job_execution_id)


@rest.patch('/job-executions/<job_execution_id>')
@acl.enforce("data-processing:job-executions:modify")
@v.check_exists(api.get_job_execution, id='job_execution_id')
@v.validate(
    v_j_e_schema.JOB_EXEC_UPDATE_SCHEMA, v_j_e.check_job_execution_update)
def job_executions_update(job_execution_id, data):
    return u.to_wrapped_dict(
        api.update_job_execution, job_execution_id, data)


@rest.delete('/job-executions/<job_execution_id>')
@acl.enforce("data-processing:job-executions:delete")
@v.check_exists(api.get_job_execution, id='job_execution_id')
@v.validate(None, v_j_e.check_job_execution_delete)
def job_executions_delete(job_execution_id):
    api.delete_job_execution(job_execution_id)
    return u.render()
