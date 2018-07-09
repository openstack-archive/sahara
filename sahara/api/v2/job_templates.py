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


@rest.get('/job-templates')
@acl.enforce("data-processing:job-templates:get_all")
@v.check_exists(api.get_job_templates, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_jobs)
def job_templates_list():
    result = api.get_job_templates(**u.get_request_args().to_dict())
    return u.render(res=result, name='job_templates')


@rest.post('/job-templates')
@acl.enforce("data-processing:job-templates:create")
@v.validate(v_j_schema.JOB_SCHEMA, v_j.check_mains_libs, v_j.check_interface)
def job_templates_create(data):
    return u.render({'job_template': api.create_job_template(data).to_dict()})


@rest.get('/job-templates/<job_templates_id>')
@acl.enforce("data-processing:job-templates:get")
@v.check_exists(api.get_job_templates, id='job_templates_id')
def job_templates_get(job_templates_id):
    return u.render({'job_template': api.get_job_template(
        job_templates_id).to_dict()})


@rest.patch('/job-templates/<job_templates_id>')
@acl.enforce("data-processing:jobs:modify")
@v.check_exists(api.get_job_templates, id='job_templates_id')
@v.validate(v_j_schema.JOB_UPDATE_SCHEMA)
def job_templates_update(job_templates_id, data):
    return u.render({'job_template': api.update_job_template(
        job_templates_id, data).to_dict()})


@rest.delete('/job-templates/<job_templates_id>')
@acl.enforce("data-processing:jobs:delete")
@v.check_exists(api.get_job_templates, id='job_templates_id')
def job_templates_delete(job_templates_id):
    api.delete_job_template(job_templates_id)
    return u.render()


@rest.get('/job-templates/config-hints/<job_type>')
@acl.enforce("data-processing:jobs:get_config_hints")
@v.check_exists(api.get_job_config_hints, job_type='job_type')
def job_config_hints_get(job_type):
    return u.render(api.get_job_config_hints(job_type))
