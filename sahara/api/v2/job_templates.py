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
from sahara.service.api.v2 import job_templates as api
from sahara.service import validation as v
from sahara.service.validations.edp import job as v_j
from sahara.service.validations.edp import job_schema as v_j_schema
import sahara.utils.api as u


rest = u.RestV2('job-templates', __name__)


def _replace_tenant_id_project_id_job_binary(jb_list):
    for jb_obj in jb_list:
        dict.update(jb_obj, {'project_id': jb_obj['tenant_id']})
        dict.pop(jb_obj, 'tenant_id')


@rest.get('/job-templates')
@acl.enforce("data-processing:job-template:list")
@v.check_exists(api.get_job_template, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_jobs)
@v.validate_request_params(['type', 'name'])
def job_templates_list():
    result = api.get_job_templates(**u.get_request_args().to_dict())
    for jt in result:
        u._replace_tenant_id_project_id(jt)
        _replace_tenant_id_project_id_job_binary(jt['mains'])
        _replace_tenant_id_project_id_job_binary(jt['libs'])
    return u.render(res=result, name='job_templates')


@rest.post('/job-templates')
@acl.enforce("data-processing:job-template:create")
@v.validate(v_j_schema.JOB_SCHEMA, v_j.check_mains_libs, v_j.check_interface)
@v.validate_request_params([])
def job_templates_create(data):
    result = {'job_template': api.create_job_template(data).to_dict()}
    u._replace_tenant_id_project_id(result['job_template'])
    _replace_tenant_id_project_id_job_binary(result['job_template']['mains'])
    _replace_tenant_id_project_id_job_binary(result['job_template']['libs'])
    return u.render(result)


@rest.get('/job-templates/<job_templates_id>')
@acl.enforce("data-processing:job-template:get")
@v.check_exists(api.get_job_template, id='job_templates_id')
@v.validate_request_params([])
def job_templates_get(job_templates_id):
    result = {'job_template': api.get_job_template(
        job_templates_id).to_dict()}
    u._replace_tenant_id_project_id(result['job_template'])
    _replace_tenant_id_project_id_job_binary(result['job_template']['mains'])
    _replace_tenant_id_project_id_job_binary(result['job_template']['libs'])
    return u.render(result)


@rest.patch('/job-templates/<job_templates_id>')
@acl.enforce("data-processing:job-template:update")
@v.check_exists(api.get_job_template, id='job_templates_id')
@v.validate(v_j_schema.JOB_UPDATE_SCHEMA)
@v.validate_request_params([])
def job_templates_update(job_templates_id, data):
    result = {'job_template': api.update_job_template(
        job_templates_id, data).to_dict()}
    u._replace_tenant_id_project_id(result['job_template'])
    _replace_tenant_id_project_id_job_binary(result['job_template']['mains'])
    _replace_tenant_id_project_id_job_binary(result['job_template']['libs'])
    return u.render(result)


@rest.delete('/job-templates/<job_templates_id>')
@acl.enforce("data-processing:job-template:delete")
@v.check_exists(api.get_job_template, id='job_templates_id')
@v.validate_request_params([])
def job_templates_delete(job_templates_id):
    api.delete_job_template(job_templates_id)
    return u.render()


@rest.get('/job-templates/config-hints/<job_type>')
@acl.enforce("data-processing:job-template:get-config-hints")
@v.check_exists(api.get_job_config_hints, job_type='job_type')
@v.validate_request_params([])
def job_config_hints_get(job_type):
    return u.render(api.get_job_config_hints(job_type))
