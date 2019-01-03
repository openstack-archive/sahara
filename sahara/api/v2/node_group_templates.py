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
from sahara.service.api.v2 import node_group_templates as api
from sahara.service import validation as v
from sahara.service.validations import node_group_template_schema as ngt_schema
from sahara.service.validations import node_group_templates as v_ngt
import sahara.utils.api as u


rest = u.RestV2('node-group-templates', __name__)


@rest.get('/node-group-templates')
@acl.enforce("data-processing:node-group-template:list")
@v.check_exists(api.get_node_group_template, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_node_group_templates)
@v.validate_request_params(['plugin_name', 'plugin_version', 'name'])
def node_group_templates_list():
    request_args = u.get_request_args().to_dict()
    if 'plugin_version' in request_args:
        request_args['hadoop_version'] = request_args['plugin_version']
        del request_args['plugin_version']
    result = api.get_node_group_templates(**request_args)
    for ngt in result:
        u._replace_hadoop_version_plugin_version(ngt)
        u._replace_tenant_id_project_id(ngt)
    return u.render(res=result, name="node_group_templates")


@rest.post('/node-group-templates')
@acl.enforce("data-processing:node-group-template:create")
@v.validate(ngt_schema.NODE_GROUP_TEMPLATE_SCHEMA_V2,
            v_ngt.check_node_group_template_create)
@v.validate_request_params([])
def node_group_templates_create(data):
    # renaming hadoop_version -> plugin_version
    # this can be removed once APIv1 is deprecated
    data['hadoop_version'] = data['plugin_version']
    del data['plugin_version']
    result = api.create_node_group_template(data).to_wrapped_dict()
    u._replace_hadoop_version_plugin_version(result['node_group_template'])
    u._replace_tenant_id_project_id(result['node_group_template'])
    return u.render(result)


@rest.get('/node-group-templates/<node_group_template_id>')
@acl.enforce("data-processing:node-group-template:get")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate_request_params([])
def node_group_templates_get(node_group_template_id):
    result = u.to_wrapped_dict_no_render(
        api.get_node_group_template, node_group_template_id)
    u._replace_hadoop_version_plugin_version(result['node_group_template'])
    u._replace_tenant_id_project_id(result['node_group_template'])
    return u.render(result)


@rest.patch('/node-group-templates/<node_group_template_id>')
@acl.enforce("data-processing:node-group-template:update")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate(ngt_schema.NODE_GROUP_TEMPLATE_UPDATE_SCHEMA_V2,
            v_ngt.check_node_group_template_update)
@v.validate_request_params([])
def node_group_templates_update(node_group_template_id, data):
    if data.get('plugin_version', None):
        data['hadoop_version'] = data['plugin_version']
        del data['plugin_version']
    result = u.to_wrapped_dict_no_render(
        api.update_node_group_template, node_group_template_id, data)
    u._replace_hadoop_version_plugin_version(result['node_group_template'])
    u._replace_tenant_id_project_id(result['node_group_template'])
    return u.render(result)


@rest.delete('/node-group-templates/<node_group_template_id>')
@acl.enforce("data-processing:node-group-template:delete")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate(None, v_ngt.check_node_group_template_usage)
@v.validate_request_params([])
def node_group_templates_delete(node_group_template_id):
    api.terminate_node_group_template(node_group_template_id)
    return u.render()


def _node_group_template_export_helper(template):
    template.pop('id')
    template.pop('updated_at')
    template.pop('created_at')
    template.pop('project_id')
    template.pop('is_default')
    template['flavor_id'] = '{flavor_id}'
    template['security_groups'] = '{security_groups}'
    template['image_id'] = '{image_id}'
    template['floating_ip_pool'] = '{floating_ip_pool}'


@rest.get('/node-group-templates/<node_group_template_id>/export')
@acl.enforce("data-processing:node-group-template:get")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate_request_params([])
def node_group_template_export(node_group_template_id):
    content = u.to_wrapped_dict_no_render(
        api.export_node_group_template, node_group_template_id)
    u._replace_hadoop_version_plugin_version(content['node_group_template'])
    u._replace_tenant_id_project_id(content['node_group_template'])
    _node_group_template_export_helper(content['node_group_template'])
    res = u.render(content)
    res.headers.add('Content-Disposition', 'attachment',
                    filename='node_group_template.json')
    return res
