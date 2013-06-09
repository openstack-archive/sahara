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

import abc
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
    @abc.abstractmethod
    def get_versions(self):
        pass

    @abc.abstractmethod
    def get_configs(self, hadoop_version):
        pass

    @abc.abstractmethod
    def get_node_processes(self, hadoop_version):
        pass

    def validate(self, cluster):
        pass

    def update_infra(self, cluster):
        pass

    @abc.abstractmethod
    def configure_cluster(self, cluster):
        pass

    @abc.abstractmethod
    def start_cluster(self, cluster):
        pass

    def convert(self, cluster, input_file):
        pass

    def on_terminate_cluster(self, cluster):
        pass

    def to_dict(self):
        res = super(ProvisioningPluginBase, self).to_dict()
        res['versions'] = self.get_versions()
        return res


class Config(resources.BaseResource):
    """Describes a single config parameter.

    Config type - could be 'str', 'integer', 'boolean', 'enum'.
    If config type is 'enum' then list of valid values should be specified in
    config_values property.

    For example:

        "some_conf", "map_reduce", "node", is_optional=True
    """

    def __init__(self, name, applicable_target, scope, config_type="str",
                 config_values=None, default_value=None, is_optional=False,
                 description=None):
        self.name = name
        self.description = description
        self.config_type = config_type
        self.config_values = config_values
        self.default_value = default_value
        self.applicable_target = applicable_target
        self.scope = scope
        self.is_optional = is_optional

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

    def __repr__(self):
        return '<UserInput %s = %s>' % (self.config.name, self.value)


class ValidationError(object):
    """Describes what is wrong with one of the values provided by user."""

    def __init__(self, config, message):
        self.config = config
        self.message = message

    def __repr__(self):
        return "<ValidationError %s>" % self.config.name
