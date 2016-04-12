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


@rest.post_file('/plugins/<plugin_name>/<version>/convert-config/<name>')
@acl.enforce("data-processing:plugins:convert_config")
@v.check_exists(api.get_plugin, plugin_name='plugin_name', version='version')
@v.validate(v_p.CONVERT_TO_TEMPLATE_SCHEMA, v_p.check_convert_to_template)
def plugins_convert_to_cluster_template(plugin_name, version, name, data):
    return u.to_wrapped_dict(
        api.convert_to_cluster_template, plugin_name, version, name, data)
