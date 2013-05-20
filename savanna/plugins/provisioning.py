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

from abc import abstractmethod
import functools
from savanna.plugins.base import PluginInterface
import savanna.utils.openstack.nova as nova
from savanna.utils.resources import BaseResource


class ProvisioningPluginContext(object):
    def __init__(self, headers):
        self.headers = headers
        self.nova = self._autoheaders(nova.novaclient)

    def _autoheaders(self, func):
        return functools.partial(func, headers=self.headers)


class ProvisioningPluginBase(PluginInterface):
    @abstractmethod
    def get_versions(self):
        pass

    @abstractmethod
    def get_configs(self, ctx, hadoop_version):
        pass

    @abstractmethod
    def get_node_processes(self, ctx, hadoop_version):
        pass

    def validate(self, ctx, cluster):
        pass

    def update_infra(self, ctx, cluster):
        pass

    @abstractmethod
    def configure_cluster(self, ctx, cluster):
        pass

    @abstractmethod
    def start_cluster(self, ctx, cluster):
        pass

    def convert(self, ctx, cluster, input_file):
        pass

    def on_terminate_cluster(self, ctx, cluster):
        pass

    def to_dict(self):
        res = super(ProvisioningPluginBase, self).to_dict()
        res['versions'] = self.get_versions()
        return res


class Config(BaseResource):
    """Describes a single config parameter.

    For example:

        "some_conf", "jot_tracker", is_optional=True
    """

    def __init__(self, name, applicable_target, config_type="str",
                 config_values=None, default_value=None, is_optional=False,
                 description=None):
        self.name = name
        self.applicable_target = applicable_target
        self.config_type = config_type
        self.config_values = config_values
        self.default_value = default_value
        self.is_optional = is_optional
        self.description = description

    def to_dict(self):
        res = super(Config, self).to_dict()
        # todo all custom fields from res
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
