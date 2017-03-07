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


from sahara.api import acl
from sahara.service.api import v11 as api
from sahara.service import validation as v
from sahara.service.validations.edp import data_source as v_d_s
from sahara.service.validations.edp import data_source_schema as v_d_s_schema
from sahara.service.validations.edp import job as v_j
from sahara.service.validations.edp import job_binary as v_j_b
from sahara.service.validations.edp import job_binary_internal as v_j_b_i
from sahara.service.validations.edp import job_binary_internal_schema as vjbi_s
from sahara.service.validations.edp import job_binary_schema as v_j_b_schema
from sahara.service.validations.edp import job_execution as v_j_e
from sahara.service.validations.edp import job_execution_schema as v_j_e_schema
from sahara.service.validations.edp import job_schema as v_j_schema
import sahara.utils.api as u


rest = u.Rest('v11', __name__)


# Job execution ops

@rest.get('/job-executions')
@acl.enforce("data-processing:job-executions:get_all")
@v.check_exists(api.get_job_execution, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_job_executions)
def job_executions_list():
    result = api.job_execution_list(
        **u.get_request_args().to_dict())
    return u.render(res=result, name='job_executions')


@rest.get('/job-executions/<job_id>')
@acl.enforce("data-processing:job-executions:get")
@v.check_exists(api.get_job_execution, id='job_id')
def job_executions(job_id):
    return u.to_wrapped_dict(api.get_job_execution, job_id)


@rest.get('/job-executions/<job_id>/refresh-status')
@acl.enforce("data-processing:job-executions:refresh_status")
@v.check_exists(api.get_job_execution, id='job_id')
def job_executions_status(job_id):
    return u.to_wrapped_dict(api.get_job_execution_status, job_id)


@rest.get('/job-executions/<job_id>/cancel')
@acl.enforce("data-processing:job-executions:cancel")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(None, v_j_e.check_job_execution_cancel)
def job_executions_cancel(job_id):
    return u.to_wrapped_dict(api.cancel_job_execution, job_id)


@rest.patch('/job-executions/<job_id>')
@acl.enforce("data-processing:job-executions:modify")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(v_j_e_schema.JOB_EXEC_UPDATE_SCHEMA,
            v_j_e.check_job_execution_update,
            v_j_e.check_job_status_update)
def job_executions_update(job_id, data):
    return u.to_wrapped_dict(api.update_job_execution, job_id, data)


@rest.delete('/job-executions/<job_id>')
@acl.enforce("data-processing:job-executions:delete")
@v.check_exists(api.get_job_execution, id='job_id')
@v.validate(None, v_j_e.check_job_execution_delete)
def job_executions_delete(job_id):
    api.delete_job_execution(job_id)
    return u.render()


# Data source ops

@rest.get('/data-sources')
@acl.enforce("data-processing:data-sources:get_all")
@v.check_exists(api.get_data_source, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_data_sources)
def data_sources_list():
    result = api.get_data_sources(**u.get_request_args().to_dict())
    return u.render(res=result, name='data_sources')


@rest.post('/data-sources')
@acl.enforce("data-processing:data-sources:register")
@v.validate(v_d_s_schema.DATA_SOURCE_SCHEMA, v_d_s.check_data_source_create)
def data_source_register(data):
    return u.render(api.register_data_source(data).to_wrapped_dict())


@rest.get('/data-sources/<data_source_id>')
@acl.enforce("data-processing:data-sources:get")
@v.check_exists(api.get_data_source, 'data_source_id')
def data_source_get(data_source_id):
    return u.to_wrapped_dict(api.get_data_source, data_source_id)


@rest.delete('/data-sources/<data_source_id>')
@acl.enforce("data-processing:data-sources:delete")
@v.check_exists(api.get_data_source, 'data_source_id')
def data_source_delete(data_source_id):
    api.delete_data_source(data_source_id)
    return u.render()


@rest.put('/data-sources/<data_source_id>')
@acl.enforce("data-processing:data-sources:modify")
@v.check_exists(api.get_data_source, 'data_source_id')
@v.validate(
    v_d_s_schema.DATA_SOURCE_UPDATE_SCHEMA, v_d_s.check_data_source_update)
def data_source_update(data_source_id, data):
    return u.to_wrapped_dict(api.data_source_update, data_source_id, data)


# Job ops

@rest.get('/jobs')
@acl.enforce("data-processing:jobs:get_all")
@v.check_exists(api.get_job, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_jobs)
def job_list():

    result = api.get_jobs(**u.get_request_args().to_dict())

    return u.render(res=result, name='jobs')


@rest.post('/jobs')
@acl.enforce("data-processing:jobs:create")
@v.validate(v_j_schema.JOB_SCHEMA, v_j.check_mains_libs, v_j.check_interface)
def job_create(data):
    return u.render(api.create_job(data).to_wrapped_dict())


@rest.get('/jobs/<job_templates_id>')
@acl.enforce("data-processing:jobs:get")
@v.check_exists(api.get_job, id='job_templates_id')
def job_get(job_templates_id):
    return u.to_wrapped_dict(api.get_job, job_templates_id)


@rest.patch('/jobs/<job_templates_id>')
@acl.enforce("data-processing:jobs:modify")
@v.check_exists(api.get_job, id='job_templates_id')
@v.validate(v_j_schema.JOB_UPDATE_SCHEMA)
def job_update(job_templates_id, data):
    return u.to_wrapped_dict(api.update_job, job_templates_id, data)


@rest.delete('/jobs/<job_templates_id>')
@acl.enforce("data-processing:jobs:delete")
@v.check_exists(api.get_job, id='job_templates_id')
def job_delete(job_templates_id):
    api.delete_job(job_templates_id)
    return u.render()


@rest.post('/jobs/<job_templates_id>/execute')
@acl.enforce("data-processing:jobs:execute")
@v.check_exists(api.get_job, id='job_templates_id')
@v.validate(v_j_e_schema.JOB_EXEC_SCHEMA, v_j_e.check_job_execution)
def job_execute(job_templates_id, data):
    return u.render(job_execution=api.execute_job(
        job_templates_id, data).to_dict())


@rest.get('/jobs/config-hints/<job_type>')
@acl.enforce("data-processing:jobs:get_config_hints")
@v.check_exists(api.get_job_config_hints, job_type='job_type')
def job_config_hints_get(job_type):
    return u.render(api.get_job_config_hints(job_type))


@rest.get('/job-types')
@acl.enforce("data-processing:job-types:get_all")
def job_types_get():
    # We want to use flat=False with to_dict() so that
    # the value of each arg is given as a list. This supports
    # filters of the form ?type=Pig&type=Java, etc.
    return u.render(job_types=api.get_job_types(
        **u.get_request_args().to_dict(flat=False)))

# Job binary ops


@rest.post('/job-binaries')
@acl.enforce("data-processing:job-binaries:create")
@v.validate(v_j_b_schema.JOB_BINARY_SCHEMA, v_j_b.check_job_binary)
def job_binary_create(data):
    return u.render(api.create_job_binary(data).to_wrapped_dict())


@rest.get('/job-binaries')
@acl.enforce("data-processing:job-binaries:get_all")
@v.check_exists(api.get_job_binaries, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_job_binaries)
def job_binary_list():
    result = api.get_job_binaries(**u.get_request_args().to_dict())

    return u.render(res=result, name='binaries')


@rest.get('/job-binaries/<job_binary_id>')
@acl.enforce("data-processing:job-binaries:get")
@v.check_exists(api.get_job_binary, 'job_binary_id')
def job_binary_get(job_binary_id):
    return u.to_wrapped_dict(api.get_job_binary, job_binary_id)


@rest.delete('/job-binaries/<job_binary_id>')
@acl.enforce("data-processing:job-binaries:delete")
@v.check_exists(api.get_job_binary, id='job_binary_id')
def job_binary_delete(job_binary_id):
    api.delete_job_binary(job_binary_id)
    return u.render()


@rest.get('/job-binaries/<job_binary_id>/data')
@acl.enforce("data-processing:job-binaries:get_data")
@v.check_exists(api.get_job_binary, 'job_binary_id')
def job_binary_data(job_binary_id):
    data = api.get_job_binary_data(job_binary_id)
    if type(data) == dict:
        data = u.render(data)
    return data


@rest.put('/job-binaries/<job_binary_id>')
@acl.enforce("data-processing:job-binaries:modify")
@v.validate(v_j_b_schema.JOB_BINARY_UPDATE_SCHEMA, v_j_b.check_job_binary)
def job_binary_update(job_binary_id, data):
    return u.render(api.update_job_binary(job_binary_id,
                                          data).to_wrapped_dict())


# Job binary internals ops

@rest.put_file('/job-binary-internals/<name>')
@acl.enforce("data-processing:job-binary-internals:create")
@v.validate(None, v_j_b_i.check_job_binary_internal)
def job_binary_internal_create(**values):
    return u.render(api.create_job_binary_internal(values).to_wrapped_dict())


@rest.get('/job-binary-internals')
@acl.enforce("data-processing:job-binary-internals:get_all")
@v.check_exists(api.get_job_binary_internal, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_job_binary_internals)
def job_binary_internal_list():
    result = api.get_job_binary_internals(**u.get_request_args().to_dict())
    return u.render(res=result, name='binaries')


@rest.get('/job-binary-internals/<job_binary_internal_id>')
@acl.enforce("data-processing:job-binary-internals:get")
@v.check_exists(api.get_job_binary_internal, 'job_binary_internal_id')
def job_binary_internal_get(job_binary_internal_id):
    return u.to_wrapped_dict(
        api.get_job_binary_internal, job_binary_internal_id)


@rest.delete('/job-binary-internals/<job_binary_internal_id>')
@acl.enforce("data-processing:job-binary-internals:delete")
@v.check_exists(api.get_job_binary_internal, 'job_binary_internal_id')
def job_binary_internal_delete(job_binary_internal_id):
    api.delete_job_binary_internal(job_binary_internal_id)
    return u.render()


@rest.get('/job-binary-internals/<job_binary_internal_id>/data')
@acl.enforce("data-processing:job-binary-internals:get_data")
@v.check_exists(api.get_job_binary_internal, 'job_binary_internal_id')
def job_binary_internal_data(job_binary_internal_id):
    return api.get_job_binary_internal_data(job_binary_internal_id)


@rest.patch('/job-binary-internals/<job_binary_internal_id>')
@acl.enforce("data-processing:job-binaries:modify")
@v.check_exists(api.get_job_binary_internal, 'job_binary_internal_id')
@v.validate(vjbi_s.JOB_BINARY_UPDATE_SCHEMA)
def job_binary_internal_update(job_binary_internal_id, data):
    return u.to_wrapped_dict(
        api.update_job_binary_internal, job_binary_internal_id, data)
