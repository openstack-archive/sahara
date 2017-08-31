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

import six

from sahara.api import acl
from sahara.service.api import v10 as api
from sahara.service import validation as v
from sahara.service.validations import cluster_template_schema as ct_schema
from sahara.service.validations import cluster_templates as v_ct
from sahara.service.validations import clusters as v_c
from sahara.service.validations import clusters_scaling as v_c_s
from sahara.service.validations import clusters_schema as v_c_schema
from sahara.service.validations import images as v_images
from sahara.service.validations import node_group_template_schema as ngt_schema
from sahara.service.validations import node_group_templates as v_ngt
from sahara.service.validations import plugins as v_p
import sahara.utils.api as u


rest = u.Rest('v10', __name__)


# Cluster ops

@rest.get('/clusters')
@acl.enforce("data-processing:clusters:get_all")
@v.check_exists(api.get_cluster, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_clusters)
def clusters_list():
    result = api.get_clusters(**u.get_request_args().to_dict())
    return u.render(res=result, name='clusters')


@rest.post('/clusters')
@acl.enforce("data-processing:clusters:create")
@v.validate(v_c_schema.CLUSTER_SCHEMA, v_c.check_cluster_create)
def clusters_create(data):
    return u.render(api.create_cluster(data).to_wrapped_dict())


@rest.post('/clusters/multiple')
@acl.enforce("data-processing:clusters:create")
@v.validate(
    v_c_schema.MULTIPLE_CLUSTER_SCHEMA, v_c.check_multiple_clusters_create)
def clusters_create_multiple(data):
    return u.render(api.create_multiple_clusters(data))


@rest.put('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:scale")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_schema.CLUSTER_SCALING_SCHEMA, v_c_s.check_cluster_scaling)
def clusters_scale(cluster_id, data):
    return u.to_wrapped_dict(api.scale_cluster, cluster_id, data)


@rest.get('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:get")
@v.check_exists(api.get_cluster, 'cluster_id')
def clusters_get(cluster_id):
    data = u.get_request_args()
    show_events = six.text_type(
        data.get('show_progress', 'false')).lower() == 'true'
    return u.to_wrapped_dict(api.get_cluster, cluster_id, show_events)


@rest.patch('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:modify")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_schema.CLUSTER_UPDATE_SCHEMA, v_c.check_cluster_update)
def clusters_update(cluster_id, data):
    return u.to_wrapped_dict(api.update_cluster, cluster_id, data)


@rest.delete('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:delete")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(None, v_c.check_cluster_delete)
def clusters_delete(cluster_id):
    api.terminate_cluster(cluster_id)
    return u.render()


# ClusterTemplate ops

@rest.get('/cluster-templates')
@acl.enforce("data-processing:cluster-templates:get_all")
@v.check_exists(api.get_cluster_template, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_cluster_templates)
def cluster_templates_list():
    result = api.get_cluster_templates(
        **u.get_request_args().to_dict())

    return u.render(res=result, name='cluster_templates')


@rest.post('/cluster-templates')
@acl.enforce("data-processing:cluster-templates:create")
@v.validate(ct_schema.CLUSTER_TEMPLATE_SCHEMA,
            v_ct.check_cluster_template_create)
def cluster_templates_create(data):
    return u.render(api.create_cluster_template(data).to_wrapped_dict())


@rest.get('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-templates:get")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
def cluster_templates_get(cluster_template_id):
    return u.to_wrapped_dict(api.get_cluster_template, cluster_template_id)


@rest.put('/cluster-templates/<cluster_template_id>')
@acl.enforce("data-processing:cluster-templates:modify")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate(ct_schema.CLUSTER_TEMPLATE_UPDATE_SCHEMA,
            v_ct.check_cluster_template_update)
def cluster_templates_update(cluster_template_id, data):
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
        api.get_cluster_template, cluster_template_id)
    _cluster_template_export_helper(content['cluster_template'])
    res = u.render(content)
    res.headers.add('Content-Disposition', 'attachment',
                    filename='cluster_template.json')
    return res


# NodeGroupTemplate ops

@rest.get('/node-group-templates')
@acl.enforce("data-processing:node-group-templates:get_all")
@v.check_exists(api.get_node_group_template, 'marker')
@v.validate(None, v.validate_pagination_limit,
            v.validate_sorting_node_group_templates)
def node_group_templates_list():
    result = api.get_node_group_templates(
        **u.get_request_args().to_dict())
    return u.render(res=result, name='node_group_templates')


@rest.post('/node-group-templates')
@acl.enforce("data-processing:node-group-templates:create")
@v.validate(ngt_schema.NODE_GROUP_TEMPLATE_SCHEMA,
            v_ngt.check_node_group_template_create)
def node_group_templates_create(data):
    return u.render(api.create_node_group_template(data).to_wrapped_dict())


@rest.get('/node-group-templates/<node_group_template_id>')
@acl.enforce("data-processing:node-group-templates:get")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
def node_group_templates_get(node_group_template_id):
    return u.to_wrapped_dict(
        api.get_node_group_template, node_group_template_id)


@rest.put('/node-group-templates/<node_group_template_id>')
@acl.enforce("data-processing:node-group-templates:modify")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate(ngt_schema.NODE_GROUP_TEMPLATE_UPDATE_SCHEMA,
            v_ngt.check_node_group_template_update)
def node_group_templates_update(node_group_template_id, data):
    return u.to_wrapped_dict(
        api.update_node_group_template, node_group_template_id, data)


@rest.delete('/node-group-templates/<node_group_template_id>')
@acl.enforce("data-processing:node-group-templates:delete")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate(None, v_ngt.check_node_group_template_usage)
def node_group_templates_delete(node_group_template_id):
    api.terminate_node_group_template(node_group_template_id)
    return u.render()


def _node_group_template_export_helper(template):
    template.pop('id')
    template.pop('updated_at')
    template.pop('created_at')
    template.pop('tenant_id')
    template.pop('is_default')
    template['flavor_id'] = '{flavor_id}'
    template['security_groups'] = '{security_groups}'
    template['image_id'] = '{image_id}'
    template['floating_ip_pool'] = '{floating_ip_pool}'


@rest.get('/node-group-templates/<node_group_template_id>/export')
@acl.enforce("data-processing:node-group-templates:get")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
def node_group_template_export(node_group_template_id):
    content = u.to_wrapped_dict_no_render(
        api.export_node_group_template, node_group_template_id)
    _node_group_template_export_helper(content['node_group_template'])
    res = u.render(content)
    res.headers.add('Content-Disposition', 'attachment',
                    filename='node_group_template.json')
    return res


# Plugins ops

@rest.get('/plugins')
@acl.enforce("data-processing:plugins:get_all")
def plugins_list():
    return u.render(plugins=[p.dict for p in api.get_plugins()])


@rest.get('/plugins/<plugin_name>')
@acl.enforce("data-processing:plugins:get")
@v.check_exists(api.get_plugin, plugin_name='plugin_name')
def plugins_get(plugin_name):
    return u.render(api.get_plugin(plugin_name).wrapped_dict)


@rest.get('/plugins/<plugin_name>/<version>')
@acl.enforce("data-processing:plugins:get_version")
@v.check_exists(api.get_plugin, plugin_name='plugin_name', version='version')
def plugins_get_version(plugin_name, version):
    return u.render(api.get_plugin(plugin_name, version).wrapped_dict)


@rest.patch('/plugins/<plugin_name>')
@acl.enforce("data-processing:plugins:patch")
@v.check_exists(api.get_plugin, plugin_name='plugin_name')
@v.validate(v_p.plugin_update_validation_jsonschema(), v_p.check_plugin_update)
def plugins_update(plugin_name, data):
    return u.render(api.update_plugin(plugin_name, data).wrapped_dict)


@rest.post_file('/plugins/<plugin_name>/<version>/convert-config/<name>')
@acl.enforce("data-processing:plugins:convert_config")
@v.check_exists(api.get_plugin, plugin_name='plugin_name', version='version')
@v.validate(None, v_p.check_convert_to_template)
def plugins_convert_to_cluster_template(plugin_name, version, name, data):
    # There is no plugins that supports converting to cluster template
    # The last plugin with support of that is no longer supported
    pass


# Image Registry ops

@rest.get('/images')
@acl.enforce("data-processing:images:get_all")
def images_list():
    tags = u.get_request_args().getlist('tags')
    name = u.get_request_args().get('name', None)
    return u.render(images=[i.dict for i in api.get_images(name, tags)])


@rest.get('/images/<image_id>')
@acl.enforce("data-processing:images:get")
@v.check_exists(api.get_image, id='image_id')
def images_get(image_id):
    return u.render(api.get_registered_image(image_id=image_id).wrapped_dict)


@rest.post('/images/<image_id>')
@acl.enforce("data-processing:images:register")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_register_schema, v_images.check_image_register)
def images_set(image_id, data):
    return u.render(api.register_image(image_id, **data).wrapped_dict)


@rest.delete('/images/<image_id>')
@acl.enforce("data-processing:images:unregister")
@v.check_exists(api.get_image, id='image_id')
def images_unset(image_id):
    api.unregister_image(image_id)
    return u.render()


@rest.post('/images/<image_id>/tag')
@acl.enforce("data-processing:images:add_tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_tags_schema, v_images.check_tags)
def image_tags_add(image_id, data):
    return u.render(api.add_image_tags(image_id, **data).wrapped_dict)


@rest.post('/images/<image_id>/untag')
@acl.enforce("data-processing:images:remove_tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_tags_schema)
def image_tags_delete(image_id, data):
    return u.render(api.remove_image_tags(image_id, **data).wrapped_dict)
