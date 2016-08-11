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
from sahara.service.api.v2 import job_executions as j_e_api
from sahara.service.api.v2 import jobs as api
from sahara.service import validation as v
from sahara.service.validations.edp import job as v_j
from sahara.service.validations.edp import job_execution as v_j_e
from sahara.service.validations.edp import job_execution_schema as v_j_e_schema
from sahara.service.validations.edp import job_schema as v_j_schema
import sahara.utils.api as u


rest = u.RestV2('jobs', __name__)


@rest.get('/job-templates')
@acl.enforce("data-processing:jobs:get_all")
@v.check_exists(api.get_job, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_jobs)
def job_list():
    result = api.get_jobs(**u.get_request_args().to_dict())
    return u.render(res=result, name='job_templates')


@rest.post('/job-templates')
@acl.enforce("data-processing:jobs:create")
@v.validate(v_j_schema.JOB_SCHEMA, v_j.check_mains_libs, v_j.check_interface)
def job_create(data):
    return u.render(api.create_job(data).to_wrapped_dict())


@rest.get('/job-templates/<job_id>')
@acl.enforce("data-processing:jobs:get")
@v.check_exists(api.get_job, id='job_id')
def job_get(job_id):
    return u.to_wrapped_dict(api.get_job, job_id)


@rest.patch('/job-templates/<job_id>')
@acl.enforce("data-processing:jobs:modify")
@v.check_exists(api.get_job, id='job_id')
@v.validate(v_j_schema.JOB_UPDATE_SCHEMA)
def job_update(job_id, data):
    return u.to_wrapped_dict(api.update_job, job_id, data)


@rest.delete('/job-templates/<job_id>')
@acl.enforce("data-processing:jobs:delete")
@v.check_exists(api.get_job, id='job_id')
def job_delete(job_id):
    api.delete_job(job_id)
    return u.render()


@rest.post('/job-templates/<job_id>/execute')
@acl.enforce("data-processing:jobs:execute")
@v.check_exists(api.get_job, id='job_id')
@v.validate(v_j_e_schema.JOB_EXEC_SCHEMA, v_j_e.check_job_execution)
def job_execute(job_id, data):
    return u.render(job_execution=j_e_api.execute_job(job_id, data).to_dict())


@rest.get('/job-templates/config-hints/<job_type>')
@acl.enforce("data-processing:jobs:get_config_hints")
@v.check_exists(api.get_job_config_hints, job_type='job_type')
def job_config_hints_get(job_type):
    return u.render(api.get_job_config_hints(job_type))
