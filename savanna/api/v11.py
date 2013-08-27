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

from savanna.openstack.common import log as logging
from savanna.service import api as c_api
from savanna.service.edp import api
from savanna.service import validation as v
from savanna.service.validations.edp import data_source as v_d_s
from savanna.service.validations.edp import job as v_j
from savanna.service.validations.edp import job_origin as v_j_o
import savanna.utils.api as u


LOG = logging.getLogger(__name__)

rest = u.Rest('v11', __name__)


## EDP ops

@rest.get('/jobs')
def jobs_list():
    return u.render(
        jobs=[j.to_dict() for j in api.get_jobs()])


@rest.post('/jobs')
@v.validate(v_j.JOB_SCHEMA, v_j.check_job_create)
def job_create(data):
    return u.render(api.create_job(data).to_wrapped_dict())


@rest.get('/jobs/<job_id>')
@v.check_exists(api.get_job, id='job_id')
def job_get(job_id):
    return u.render(api.get_job(job_id).to_wrapped_dict())


@rest.delete('/jobs/<job_id>')
@v.check_exists(api.get_job, id='job_id')
def job_delete(job_id):
    api.delete_job(job_id)
    return u.render()


#TODO(nprivalova): path will be updated and data will contain
# params for the job. For this purpose we
# need strong validation. Will be done in next commit
@rest.post('/jobs/<job_id>/execute/from/<input_id>/to/<output_id>/on/'
           '<cluster_id>')
@v.check_exists(api.get_job, id='job_id')
@v.check_exists(api.get_data_source, id='input_id')
@v.check_exists(api.get_data_source, id='output_id')
@v.check_exists(c_api.get_cluster, 'cluster_id')
def job_execute(job_id, input_id, output_id, cluster_id, data):
    return u.render(job_execution=api.execute_job(job_id, input_id, output_id,
                                                  cluster_id).to_dict())


@rest.get('/data-sources')
def data_sources_list():
    return u.render(
        data_sources=[ds.to_dict() for ds in api.get_data_sources()])


@rest.post('/data-sources')
@v.validate(v_d_s.DATA_SOURCE_SCHEMA, v_d_s.check_data_source_create)
def data_source_register(data):
    return u.render(api.register_data_source(data).to_wrapped_dict())


@rest.get('/data-sources/<data_source_id>')
@v.check_exists(api.get_data_source, 'data_source_id')
def data_source_get(data_source_id):
    return u.render(api.get_data_source(data_source_id).to_wrapped_dict())


@rest.delete('/data-sources/<data_source_id>')
@v.check_exists(api.get_data_source, 'data_source_id')
def data_source_delete(data_source_id):
    api.delete_data_source(data_source_id)
    return u.render()


@rest.get('/job-origins')
def job_origin_list():
    return u.render(job_origins=[j.to_dict() for j in api.get_job_origins()])


@rest.post('/job-origins')
@v.validate(v_j_o.JOB_ORIGIN_SCHEMA, v_j_o.check_job_origin_create)
def job_origin_create(data):
    return u.render(api.create_job_origin(data).to_wrapped_dict())


@rest.get('/job-origins/<job_origin_id>')
@v.check_exists(api.get_job_origin, id='job_origin_id')
def job_origin_get(job_origin_id):
    return u.render(api.get_job_origin(job_origin_id).to_wrapped_dict())


@rest.delete('/job-origins/<job_origin_id>')
@v.check_exists(api.get_job_origin, id='job_origin_id')
def job_origin_delete(job_origin_id):
    api.delete_job_origin(job_origin_id)
    return u.render()


@rest.put_file('/job-binaries/<name>')
def job_binary_create(**values):
    return u.render(api.create_job_binary(values).to_wrapped_dict())


@rest.get('/job-binaries')
def job_binary_list():
    return u.render(binaries=[j.to_dict() for j in api.get_job_binaries()])


@rest.get('/job-binaries/<job_binary_id>')
@v.check_exists(api.get_job_binary, 'job_binary_id')
def job_binary_get(job_binary_id):
    return u.render(api.get_job_binary(job_binary_id).to_wrapped_dict())


@rest.delete('/job-binaries/<job_binary_id>')
@v.check_exists(api.get_job_binary, id='job_binary_id')
def job_binary_delete(job_binary_id):
    api.delete_job_binary(job_binary_id)
    return u.render()
