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
from savanna.service.edp import api
from savanna.service import validation as v
from savanna.service.validations.edp import data_source as v_d_s
from savanna.service.validations.edp import job as v_j
import savanna.utils.api as u


LOG = logging.getLogger(__name__)

rest = u.Rest('v11', __name__)


## EDP ops

@rest.get('/jobs')
def jobs_list():
    return u.render(jobs=api.get_jobs())


@rest.post('/jobs')
@v.validate(v_j.JOB_SCHEMA, v_j.check_job_create)
def job_create(data):
    return u.render(jobs=api.create_job(data))


@rest.get('/jobs/<job_id>')
@v.check_exists(api.get_job, id='job_id')
def job_get(job_id):
    return u.render(jobs=api.get_job(job_id))


@rest.delete('/jobs/<job_id>')
@v.check_exists(api.get_job, id='job_id')
def job_delete(job_id):
    return u.render(jobs=api.delete_job(job_id))


@rest.post('/jobs/<job_id>/execute/<input_id>/<output_id>')
@v.check_exists(api.get_job, id='job_id')
@v.check_exists(api.get_data_source, id='input_id')
@v.check_exists(api.get_data_source, id='output_id')
def job_execute(job_id, input_id, output_id):
    return u.render(jobs=api.execute_job(job_id, input_id, output_id))


@rest.get('/data-sources')
def data_sources_list():
    return u.render(jobs=api.get_data_sources())


@rest.post('/data-sources')
@v.validate(v_d_s.DATA_SOURCE_SCHEMA, v_d_s.check_data_source_create)
def data_source_register(data):
    return u.render(jobs=api.register_data_source(data))


@rest.get('/data-sources/<data_source_id>')
@v.check_exists(api.get_data_source, id='data_source_id')
def data_source_get(data_source_id):
    return u.render(jobs=api.get_data_source(data_source_id))


@rest.delete('/data-sources/<data_source_id>')
@v.check_exists(api.get_data_source, id='data_source_id')
def data_source_delete(data_source_id):
    return u.render(jobs=api.delete_job(data_source_id))
