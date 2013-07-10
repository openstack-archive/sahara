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

import functools

from savanna.plugins import base as plugins_base
from savanna.utils.openstack import nova
from savanna.utils import resources


class ProvisioningPluginContext(object):
    def __init__(self, headers):
        self.headers = headers
        self.nova = self._autoheaders(nova.client)

    def _autoheaders(self, func):
        return functools.partial(func, headers=self.headers)


class ProvisioningPluginBase(plugins_base.PluginInterface):
    @plugins_base.required
    def get_versions(self):
        pass

    @plugins_base.required
    def get_configs(self, hadoop_version):
        pass

    @plugins_base.required
    def get_node_processes(self, hadoop_version):
        pass

    @plugins_base.required_with_default
    def get_required_image_tags(self, hadoop_version):
        return [self.name, hadoop_version]

    @plugins_base.required_with_default
    def validate(self, cluster):
        pass

    @plugins_base.required_with_default
    def validate_scaling(self, cluster, existing, additional):
        pass

    @plugins_base.required_with_default
    def update_infra(self, cluster):
        pass

    @plugins_base.required
    def configure_cluster(self, cluster):
        pass

    @plugins_base.required
    def start_cluster(self, cluster):
        pass

    @plugins_base.optional
    def scale_cluster(self, cluster, instances):
        pass

    @plugins_base.optional
    def convert(self, hadoop_version, config_file):
        pass

    @plugins_base.required_with_default
    def on_terminate_cluster(self, cluster):
        pass

    def to_dict(self):
        res = super(ProvisioningPluginBase, self).to_dict()
        res['versions'] = self.get_versions()
        return res

    # Some helpers for plugins

    def _map_to_user_inputs(self, hadoop_version, configs):
        config_objs = self.get_configs(hadoop_version)

        # convert config objects to applicable_target -> config_name -> obj
        config_objs_map = {}
        for config_obj in config_objs:
            applicable_target = config_obj.applicable_target
            confs = config_objs_map.get(applicable_target, {})
            confs[config_obj.name] = config_obj
            config_objs_map[applicable_target] = confs

        # iterate over all configs and append UserInputs to result list
        result = []
        for applicable_target in configs:
            for config_name in configs[applicable_target]:
                confs = config_objs_map.get(applicable_target)
                if not confs:
                    # TODO(slukjanov): raise specific exception
                    raise RuntimeError("Can't find applicable target '%s'"
                                       % applicable_target)
                conf = confs.get(config_name)
                if not conf:
                    # TODO(slukjanov): raise specific exception
                    raise RuntimeError("Can't find config '%s' in '%s'"
                                       % (config_name, applicable_target))
                result.append(UserInput(
                    conf, configs[applicable_target][config_name]))

        return result


class Config(resources.BaseResource):
    """Describes a single config parameter.

    Config type - could be 'str', 'integer', 'boolean', 'enum'.
    If config type is 'enum' then list of valid values should be specified in
    config_values property.

    Priority - integer parameter which helps to differentiate all
    configurations in the UI. Priority decreases from the lower values to
    higher values.

    For example:

        "some_conf", "map_reduce", "node", is_optional=True
    """

    def __init__(self, name, applicable_target, scope, config_type="string",
                 config_values=None, default_value=None, is_optional=False,
                 description=None, priority=2):
        self.name = name
        self.description = description
        self.config_type = config_type
        self.config_values = config_values
        self.default_value = default_value
        self.applicable_target = applicable_target
        self.scope = scope
        self.is_optional = is_optional
        self.priority = priority

    def to_dict(self):
        res = super(Config, self).to_dict()
        # TODO(slukjanov): all custom fields from res
        return res

    def __repr__(self):
        return '<Config %s in %s>' % (self.name, self.applicable_target)


class UserInput(object):
    """Value provided by the Savanna user for a specific config entry."""

    def __init__(self, config, value):
        self.config = config
        self.value = value

    def __eq__(self, other):
        return self.config == other.config and self.value == other.value

    def __repr__(self):
        return '<UserInput %s = %s>' % (self.config.name, self.value)


class ValidationError(object):
    """Describes what is wrong with one of the values provided by user."""

    def __init__(self, config, message):
        self.config = config
        self.message = message

    def __repr__(self):
        return "<ValidationError %s>" % self.config.name
