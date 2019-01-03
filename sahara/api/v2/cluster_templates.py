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
from sahara.service.api.v2 import cluster_templates as api
from sahara.service import validation as v
from sahara.service.validations import cluster_template_schema as ct_schema
from sahara.service.validations import cluster_templates as v_ct
import sahara.utils.api as u


rest = u.RestV2('cluster-templates', __name__)


@rest.get('/cluster-templates')
@acl.enforce("data-processing:cluster-template:list")
@v.check_exists(api.get_cluster_template, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_cluster_templates)
@v.validate_request_params(['plugin_name', 'plugin_version', 'name'])
def cluster_templates_list():
    request_args = u.get_request_args().to_dict()
    if 'plugin_version' in request_args:
        request_args['hadoop_version'] = request_args['plugin_version']
        del request_args['plugin_version']
    result = api.get_cluster_templates(**request_args)
    for ct in result:
        u._replace_hadoop_version_plugin_version(ct)
        u._replace_tenant_id_project_id(ct)
    return u.render(res=result, name='cluster_templates')


@rest.post('/cluster-templates')
@acl.enforce("data-processing:cluster-template:create")
@v.validate(ct_schema.CLUSTER_TEMPLATE_SCHEMA_V2,
            v_ct.check_cluster_template_create)
@v.validate_request_params([])
def cluster_templates_create(data):
    # renaming hadoop_version -> plugin_version
    # this can be removed once APIv1 is deprecated
    data['hadoop_version'] = data['plugin_version']
    del data['plugin_version']
    result = api.create_cluster_template(data).to_wrapped_dict()
    u._replace_hadoop_version_plugin_version(result['cluster_template'])
    u._replace_tenant_id_project_id(result['cluster_template'])
    return u.render(result)


@rest.get('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-template:get")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate_request_params([])
def cluster_templates_get(cluster_template_id):
    result = u.to_wrapped_dict_no_render(
        api.get_cluster_template, cluster_template_id)
    u._replace_hadoop_version_plugin_version(result['cluster_template'])
    u._replace_tenant_id_project_id(result['cluster_template'])
    return u.render(result)


@rest.patch('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-template:update")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate(ct_schema.CLUSTER_TEMPLATE_UPDATE_SCHEMA_V2,
            v_ct.check_cluster_template_update)
@v.validate_request_params([])
def cluster_templates_update(cluster_template_id, data):
    if data.get('plugin_version', None):
        data['hadoop_version'] = data['plugin_version']
        del data['plugin_version']
    result = u.to_wrapped_dict_no_render(
        api.update_cluster_template, cluster_template_id, data)
    u._replace_hadoop_version_plugin_version(result['cluster_template'])
    u._replace_tenant_id_project_id(result['cluster_template'])
    return u.render(result)


@rest.delete('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-template:delete")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate(None, v_ct.check_cluster_template_usage)
@v.validate_request_params([])
def cluster_templates_delete(cluster_template_id):
    api.terminate_cluster_template(cluster_template_id)
    return u.render()


def _cluster_template_export_helper(template):
    template.pop('id')
    template.pop('updated_at')
    template.pop('created_at')
    template.pop('project_id')
    template.pop('is_default')
    template['default_image_id'] = '{default_image_id}'
    template['node_groups'] = '{node_groups}'


@rest.get('/cluster-templates/<cluster_template_id>/export')
@acl.enforce("data-processing:cluster-template:get")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate_request_params([])
def cluster_template_export(cluster_template_id):
    content = u.to_wrapped_dict_no_render(
        api.export_cluster_template, cluster_template_id)
    u._replace_hadoop_version_plugin_version(content['cluster_template'])
    u._replace_tenant_id_project_id(content['cluster_template'])
    _cluster_template_export_helper(content['cluster_template'])
    res = u.render(content)
    res.headers.add('Content-Disposition', 'attachment',
                    filename='cluster_template.json')
    return res
