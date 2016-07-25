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
from sahara.service.api.v2 import job_binaries as api
from sahara.service import validation as v
from sahara.service.validations.edp import job_binary as v_j_b
from sahara.service.validations.edp import job_binary_internal as v_j_b_i
from sahara.service.validations.edp import job_binary_internal_schema as vjbi_s
from sahara.service.validations.edp import job_binary_schema as v_j_b_schema
import sahara.utils.api as u


rest = u.RestV2('job-binaries', __name__)


@rest.post('/job-binaries')
@acl.enforce("data-processing:job-binaries:create")
@v.validate(v_j_b_schema.JOB_BINARY_SCHEMA, v_j_b.check_job_binary)
def job_binary_create(data):
    return u.render(api.create_job_binary(data).to_wrapped_dict())


@rest.get('/job-binaries')
@acl.enforce("data-processing:job-binaries:get_all")
@v.check_exists(api.get_job_binary, 'marker')
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
def job_binary_internal_list():
    return u.render(binaries=[j.to_dict() for j in
                              api.get_job_binary_internals(
                                  **u.get_request_args().to_dict())])


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
