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
from sahara.service.api.v2 import data_sources as api
from sahara.service import validation as v
from sahara.service.validations.edp import data_source as v_d_s
from sahara.service.validations.edp import data_source_schema as v_d_s_schema
import sahara.utils.api as u


rest = u.RestV2('data-sources', __name__)


@rest.get('/data-sources')
@acl.enforce("data-processing:data-source:list")
@v.check_exists(api.get_data_source, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_data_sources)
@v.validate_request_params(['type'])
def data_sources_list():
    result = api.get_data_sources(**u.get_request_args().to_dict())
    for ds in result:
        u._replace_tenant_id_project_id(ds)
    return u.render(res=result, name='data_sources')


@rest.post('/data-sources')
@acl.enforce("data-processing:data-source:register")
@v.validate(v_d_s_schema.DATA_SOURCE_SCHEMA, v_d_s.check_data_source_create)
@v.validate_request_params([])
def data_source_register(data):
    result = api.register_data_source(data).to_wrapped_dict()
    u._replace_tenant_id_project_id(result['data_source'])
    return u.render(result)


@rest.get('/data-sources/<data_source_id>')
@acl.enforce("data-processing:data-source:get")
@v.check_exists(api.get_data_source, 'data_source_id')
@v.validate_request_params([])
def data_source_get(data_source_id):
    result = api.get_data_source(data_source_id).to_wrapped_dict()
    u._replace_tenant_id_project_id(result['data_source'])
    return u.render(result)


@rest.delete('/data-sources/<data_source_id>')
@acl.enforce("data-processing:data-source:delete")
@v.check_exists(api.get_data_source, 'data_source_id')
@v.validate_request_params([])
def data_source_delete(data_source_id):
    api.delete_data_source(data_source_id)
    return u.render()


@rest.patch('/data-sources/<data_source_id>')
@acl.enforce("data-processing:data-source:update")
@v.check_exists(api.get_data_source, 'data_source_id')
@v.validate(v_d_s_schema.DATA_SOURCE_UPDATE_SCHEMA)
@v.validate_request_params([])
def data_source_update(data_source_id, data):
    result = api.data_source_update(data_source_id, data).to_wrapped_dict()
    u._replace_tenant_id_project_id(result['data_source'])
    return u.render(result)
