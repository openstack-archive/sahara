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
from sahara.service.api.v2 import clusters as api
from sahara.service import validation as v
from sahara.service.validations import clusters as v_c
from sahara.service.validations import clusters_scaling as v_c_s
from sahara.service.validations import clusters_schema as v_c_schema
import sahara.utils.api as u


rest = u.RestV2('clusters', __name__)


def _replace_tenant_id_project_id_provision_steps(c):
    if 'provision_progress' in c:
        for step in c['provision_progress']:
            dict.update(step, {'project_id': step['tenant_id']})
            dict.pop(step, 'tenant_id')


@rest.get('/clusters')
@acl.enforce("data-processing:cluster:list")
@v.check_exists(api.get_cluster, 'marker')
@v.validate(None, v.validate_pagination_limit)
@v.validate_request_params(['plugin_name', 'plugin_version', 'name'])
def clusters_list():
    request_args = u.get_request_args().to_dict()
    if 'plugin_version' in request_args:
        request_args['hadoop_version'] = request_args['plugin_version']
        del request_args['plugin_version']
    result = api.get_clusters(**request_args)
    for c in result:
        u._replace_hadoop_version_plugin_version(c)
        u._replace_tenant_id_project_id(c)
        _replace_tenant_id_project_id_provision_steps(c)
    return u.render(res=result, name='clusters')


@rest.post('/clusters')
@acl.enforce("data-processing:cluster:create")
@v.validate(v_c_schema.CLUSTER_SCHEMA_V2,
            v_c.check_one_or_multiple_clusters_create)
@v.validate_request_params([])
def clusters_create(data):
    # renaming hadoop_version -> plugin_version
    # this can be removed once APIv1 is deprecated
    data['hadoop_version'] = data['plugin_version']
    del data['plugin_version']
    if data.get('count', None) is not None:
        result = api.create_multiple_clusters(data)
        for c in result['clusters']:
            u._replace_hadoop_version_plugin_version(c['cluster'])
            u._replace_tenant_id_project_id(c['cluster'])
        return u.render(result)
    else:
        result = api.create_cluster(data).to_wrapped_dict()
        u._replace_hadoop_version_plugin_version(result['cluster'])
        u._replace_tenant_id_project_id(result['cluster'])
        return u.render(result)


@rest.put('/clusters/<cluster_id>')
@acl.enforce("data-processing:cluster:scale")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_schema.CLUSTER_SCALING_SCHEMA_V2, v_c_s.check_cluster_scaling)
@v.validate_request_params([])
def clusters_scale(cluster_id, data):
    result = u.to_wrapped_dict_no_render(
        api.scale_cluster, cluster_id, data)
    u._replace_hadoop_version_plugin_version(result['cluster'])
    u._replace_tenant_id_project_id(result['cluster'])
    _replace_tenant_id_project_id_provision_steps(result['cluster'])
    return u.render(result)


@rest.get('/clusters/<cluster_id>')
@acl.enforce("data-processing:cluster:get")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate_request_params(['show_progress'])
def clusters_get(cluster_id):
    data = u.get_request_args()
    show_events = six.text_type(
        data.get('show_progress', 'false')).lower() == 'true'
    result = u.to_wrapped_dict_no_render(
        api.get_cluster, cluster_id, show_events)
    u._replace_hadoop_version_plugin_version(result['cluster'])
    u._replace_tenant_id_project_id(result['cluster'])
    _replace_tenant_id_project_id_provision_steps(result['cluster'])
    return u.render(result)


@rest.patch('/clusters/<cluster_id>')
@acl.enforce("data-processing:cluster:update")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_schema.CLUSTER_UPDATE_SCHEMA_V2, v_c.check_cluster_update)
@v.validate_request_params([])
def clusters_update(cluster_id, data):
    result = u.to_wrapped_dict_no_render(
        api.update_cluster, cluster_id, data)
    u._replace_hadoop_version_plugin_version(result['cluster'])
    u._replace_tenant_id_project_id(result['cluster'])
    _replace_tenant_id_project_id_provision_steps(result['cluster'])
    return u.render(result)


@rest.delete('/clusters/<cluster_id>')
@acl.enforce("data-processing:cluster:delete")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_schema.CLUSTER_DELETE_SCHEMA_V2, v_c.check_cluster_delete)
@v.validate_request_params([])
def clusters_delete(cluster_id):
    data = u.request_data()
    force = data.get('force', False)
    extra = api.get_cluster(cluster_id).get('extra', {})
    stack_name = extra.get('heat_stack_name', None) if extra else None
    api.terminate_cluster(cluster_id, force=force)
    if force:
        return u.render({"stack_name": stack_name}, status=200)
    else:
        return u.render(res=None, status=204)
