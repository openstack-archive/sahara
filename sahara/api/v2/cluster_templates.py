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
@acl.enforce("data-processing:cluster-templates:get_all")
@v.check_exists(api.get_cluster_template, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_cluster_templates)
def cluster_templates_list():
    result = api.get_cluster_templates(**u.get_request_args().to_dict())
    return u.render(res=result, name='cluster_templates')


@rest.post('/cluster-templates')
@acl.enforce("data-processing:cluster-templates:create")
@v.validate(ct_schema.CLUSTER_TEMPLATE_SCHEMA_V2,
            v_ct.check_cluster_template_create)
def cluster_templates_create(data):
    # renaming hadoop_version -> plugin_version
    # this can be removed once APIv1 is deprecated
    data['hadoop_version'] = data['plugin_version']
    del data['plugin_version']
    return u.render(api.create_cluster_template(data).to_wrapped_dict())


@rest.get('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-templates:get")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
def cluster_templates_get(cluster_template_id):
    return u.to_wrapped_dict(api.get_cluster_template, cluster_template_id)


@rest.patch('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-templates:modify")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate(ct_schema.CLUSTER_TEMPLATE_UPDATE_SCHEMA_V2,
            v_ct.check_cluster_template_update)
def cluster_templates_update(cluster_template_id, data):
    if data.get('plugin_version', None):
        data['hadoop_version'] = data['plugin_version']
        del data['plugin_version']
    return u.to_wrapped_dict(
        api.update_cluster_template, cluster_template_id, data)


@rest.delete('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-templates:delete")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate(None, v_ct.check_cluster_template_usage)
def cluster_templates_delete(cluster_template_id):
    api.terminate_cluster_template(cluster_template_id)
    return u.render()


def _cluster_template_export_helper(template):
    template.pop('id')
    template.pop('updated_at')
    template.pop('created_at')
    template.pop('tenant_id')
    template.pop('is_default')
    template['default_image_id'] = '{default_image_id}'
    template['node_groups'] = '{node_groups}'


@rest.get('/cluster-templates/<cluster_template_id>/export')
@acl.enforce("data-processing:cluster-templates:get")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
def cluster_template_export(cluster_template_id):
    content = u.to_wrapped_dict_no_render(
        api.export_cluster_template, cluster_template_id)
    _cluster_template_export_helper(content['cluster_template'])
    res = u.render(content)
    res.headers.add('Content-Disposition', 'attachment',
                    filename='cluster_template.json')
    return res
