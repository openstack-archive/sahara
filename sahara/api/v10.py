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

from oslo_log import log as logging

from sahara.api import acl
from sahara.service import api
from sahara.service import validation as v
from sahara.service.validations import cluster_template_schema as ct_schema
from sahara.service.validations import cluster_templates as v_ct
from sahara.service.validations import clusters as v_c
from sahara.service.validations import clusters_scaling as v_c_s
from sahara.service.validations import images as v_images
from sahara.service.validations import node_group_template_schema as ngt_schema
from sahara.service.validations import node_group_templates as v_ngt
from sahara.service.validations import plugins as v_p
import sahara.utils.api as u


LOG = logging.getLogger(__name__)

rest = u.Rest('v10', __name__)


# Cluster ops

@rest.get('/clusters')
@acl.enforce("clusters:get_all")
def clusters_list():
    return u.render(clusters=[c.to_dict() for c in api.get_clusters(
        **u.get_request_args().to_dict())])


@rest.post('/clusters')
@acl.enforce("clusters:create")
@v.validate(v_c.CLUSTER_SCHEMA, v_c.check_cluster_create)
def clusters_create(data):
    return u.render(api.create_cluster(data).to_wrapped_dict())


@rest.put('/clusters/<cluster_id>')
@acl.enforce("clusters:scale")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_s.CLUSTER_SCALING_SCHEMA, v_c_s.check_cluster_scaling)
def clusters_scale(cluster_id, data):
    return u.render(api.scale_cluster(cluster_id, data).to_wrapped_dict())


@rest.get('/clusters/<cluster_id>')
@acl.enforce("clusters:get")
@v.check_exists(api.get_cluster, 'cluster_id')
def clusters_get(cluster_id):
    data = u.get_request_args()
    show_events = unicode(data.get('show_progress', 'false')).lower() == 'true'
    return u.render(api.get_cluster(cluster_id, show_events).to_wrapped_dict())


@rest.delete('/clusters/<cluster_id>')
@acl.enforce("clusters:delete")
@v.check_exists(api.get_cluster, 'cluster_id')
def clusters_delete(cluster_id):
    api.terminate_cluster(cluster_id)
    return u.render()


# ClusterTemplate ops

@rest.get('/cluster-templates')
@acl.enforce("cluster-templates:get_all")
def cluster_templates_list():
    return u.render(
        cluster_templates=[t.to_dict() for t in api.get_cluster_templates(
            **u.get_request_args().to_dict())])


@rest.post('/cluster-templates')
@acl.enforce("cluster-templates:create")
@v.validate(ct_schema.CLUSTER_TEMPLATE_SCHEMA,
            v_ct.check_cluster_template_create)
def cluster_templates_create(data):
    return u.render(api.create_cluster_template(data).to_wrapped_dict())


@rest.get('/cluster-templates/<cluster_template_id>')
@acl.enforce("cluster-templates:get")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
def cluster_templates_get(cluster_template_id):
    return u.render(
        api.get_cluster_template(cluster_template_id).to_wrapped_dict())


@rest.put('/cluster-templates/<cluster_template_id>')
@acl.enforce("cluster-templates:modify")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate(ct_schema.CLUSTER_TEMPLATE_UPDATE_SCHEMA,
            v_ct.check_cluster_template_update)
def cluster_templates_update(cluster_template_id, data):
    return u.render(
        api.update_cluster_template(
            cluster_template_id, data).to_wrapped_dict())


@rest.delete('/cluster-templates/<cluster_template_id>')
@acl.enforce("cluster-templates:delete")
@v.check_exists(api.get_cluster_template, 'cluster_template_id')
@v.validate(None, v_ct.check_cluster_template_usage)
def cluster_templates_delete(cluster_template_id):
    api.terminate_cluster_template(cluster_template_id)
    return u.render()


# NodeGroupTemplate ops

@rest.get('/node-group-templates')
@acl.enforce("node-group-templates:get_all")
def node_group_templates_list():
    return u.render(
        node_group_templates=[t.to_dict()
                              for t in api.get_node_group_templates(
                              **u.get_request_args().to_dict())])


@rest.post('/node-group-templates')
@acl.enforce("node-group-templates:create")
@v.validate(ngt_schema.NODE_GROUP_TEMPLATE_SCHEMA,
            v_ngt.check_node_group_template_create)
def node_group_templates_create(data):
    return u.render(api.create_node_group_template(data).to_wrapped_dict())


@rest.get('/node-group-templates/<node_group_template_id>')
@acl.enforce("node-group-templates:get")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
def node_group_templates_get(node_group_template_id):
    return u.render(
        api.get_node_group_template(node_group_template_id).to_wrapped_dict())


@rest.put('/node-group-templates/<node_group_template_id>')
@acl.enforce("node-group-templates:modify")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate(ngt_schema.NODE_GROUP_TEMPLATE_UPDATE_SCHEMA,
            v_ngt.check_node_group_template_update)
def node_group_templates_update(node_group_template_id, data):
    return u.render(
        api.update_node_group_template(node_group_template_id, data))


@rest.delete('/node-group-templates/<node_group_template_id>')
@acl.enforce("node-group-templates:delete")
@v.check_exists(api.get_node_group_template, 'node_group_template_id')
@v.validate(None, v_ngt.check_node_group_template_usage)
def node_group_templates_delete(node_group_template_id):
    api.terminate_node_group_template(node_group_template_id)
    return u.render()


# Plugins ops

@rest.get('/plugins')
@acl.enforce("plugins:get_all")
def plugins_list():
    return u.render(plugins=[p.dict for p in api.get_plugins()])


@rest.get('/plugins/<plugin_name>')
@acl.enforce("plugins:get")
@v.check_exists(api.get_plugin, plugin_name='plugin_name')
def plugins_get(plugin_name):
    return u.render(api.get_plugin(plugin_name).wrapped_dict)


@rest.get('/plugins/<plugin_name>/<version>')
@acl.enforce("plugins:get_version")
@v.check_exists(api.get_plugin, plugin_name='plugin_name', version='version')
def plugins_get_version(plugin_name, version):
    return u.render(api.get_plugin(plugin_name, version).wrapped_dict)


@rest.post_file('/plugins/<plugin_name>/<version>/convert-config/<name>')
@acl.enforce("plugins:convert_config")
@v.check_exists(api.get_plugin, plugin_name='plugin_name', version='version')
@v.validate(v_p.CONVERT_TO_TEMPLATE_SCHEMA, v_p.check_convert_to_template)
def plugins_convert_to_cluster_template(plugin_name, version, name, data):
    return u.render(api.convert_to_cluster_template(plugin_name,
                                                    version,
                                                    name,
                                                    data).to_wrapped_dict())


# Image Registry ops

@rest.get('/images')
@acl.enforce("images:get_all")
def images_list():
    tags = u.get_request_args().getlist('tags')
    name = u.get_request_args().get('name', None)
    return u.render(images=[i.dict for i in api.get_images(name, tags)])


@rest.get('/images/<image_id>')
@acl.enforce("images:get")
@v.check_exists(api.get_image, id='image_id')
def images_get(image_id):
    return u.render(api.get_registered_image(id=image_id).wrapped_dict)


@rest.post('/images/<image_id>')
@acl.enforce("images:register")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_register_schema, v_images.check_image_register)
def images_set(image_id, data):
    return u.render(api.register_image(image_id, **data).wrapped_dict)


@rest.delete('/images/<image_id>')
@acl.enforce("images:unregister")
@v.check_exists(api.get_image, id='image_id')
def images_unset(image_id):
    api.unregister_image(image_id)
    return u.render()


@rest.post('/images/<image_id>/tag')
@acl.enforce("images:add_tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_tags_schema, v_images.check_tags)
def image_tags_add(image_id, data):
    return u.render(api.add_image_tags(image_id, **data).wrapped_dict)


@rest.post('/images/<image_id>/untag')
@acl.enforce("images:remove_tags")
@v.check_exists(api.get_image, id='image_id')
@v.validate(v_images.image_tags_schema)
def image_tags_delete(image_id, data):
    return u.render(api.remove_image_tags(image_id, **data).wrapped_dict)
