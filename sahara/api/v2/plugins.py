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
from sahara.service.api.v2 import plugins as api
from sahara.service import validation as v
from sahara.service.validations import plugins as v_p
import sahara.utils.api as u


rest = u.RestV2('plugins', __name__)


@rest.get('/plugins')
@acl.enforce("data-processing:plugin:list")
@v.validate_request_params([])
def plugins_list():
    return u.render(plugins=[p.dict for p in api.get_plugins()])


@rest.get('/plugins/<plugin_name>')
@acl.enforce("data-processing:plugin:get")
@v.check_exists(api.get_plugin, plugin_name='plugin_name')
@v.validate_request_params([])
def plugins_get(plugin_name):
    return u.render(api.get_plugin(plugin_name).wrapped_dict)


@rest.get('/plugins/<plugin_name>/<version>')
@acl.enforce("data-processing:plugin:get-version")
@v.check_exists(api.get_plugin, plugin_name='plugin_name', version='version')
@v.validate_request_params([])
def plugins_get_version(plugin_name, version):
    return u.render(api.get_plugin(plugin_name, version).wrapped_dict)


@rest.patch('/plugins/<plugin_name>')
@acl.enforce("data-processing:plugin:update")
@v.check_exists(api.get_plugin, plugin_name='plugin_name')
@v.validate(v_p.plugin_update_validation_jsonschema(), v_p.check_plugin_update)
@v.validate_request_params([])
def plugins_update(plugin_name, data):
    return u.render(api.update_plugin(plugin_name, data).wrapped_dict)
