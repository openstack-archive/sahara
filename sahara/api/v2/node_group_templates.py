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
from sahara.service import api
from sahara.service import validation as v
from sahara.service.validations import node_group_template_schema as ngt_schema
from sahara.service.validations import node_group_templates as v_ngt
import sahara.utils.api as u


rest = u.RestV2('node-group-templates', __name__)


@rest.get('/node-group-templates')
@acl.enforce("data-processing:node-group-templates:get_all")
def node_group_templates_list():
    return u.render(
        node_group_templates=[t.to_dict()
                              for t in api.get_node_group_templates(
                              **u.get_request_args().to_dict())])


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
