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
import inspect

from oslo.config import cfg

from savanna import config
from savanna.openstack.common import importutils
from savanna.openstack.common import log as logging
from savanna.utils import resources

LOG = logging.getLogger(__name__)

opts = [
    cfg.ListOpt('plugins',
                default=[],
                help='List of plugins to be loaded'),
]

CONF = cfg.CONF
CONF.register_opts(opts)


class PluginInterface(resources.BaseResource):
    __metaclass__ = abc.ABCMeta

    name = 'plugin_interface'

    def get_plugin_opts(self):
        """Plugin can expose some options that should be specified in conf file

        For example:

            def get_plugin_opts(self):
            return [
                cfg.StrOpt('mandatory-conf', required=True),
                cfg.StrOpt('optional_conf', default="42"),
            ]
        """
        return []

    def setup(self, conf):
        """Plugin initialization

        :param conf: plugin-specific configurations
        """
        pass

    @abc.abstractmethod
    def get_title(self):
        """Plugin title

        For example:

            "Vanilla Provisioning"
        """
        pass

    def get_description(self):
        """Optional description of the plugin

        This information is targeted to be displayed in UI.
        """
        pass

    def to_dict(self):
        return {
            'name': self.name,
            'title': self.get_title(),
            'description': self.get_description(),
        }


class PluginManager(object):
    def __init__(self):
        self.plugins = {}
        self._load_all_plugins()

    def _load_all_plugins(self):
        LOG.debug("List of requested plugins: %s" % CONF.plugins)

        if len(CONF.plugins) > len(set(CONF.plugins)):
            raise RuntimeError("plugins config contains non-unique entries")

        # register required 'plugin_factory' property for each plugin
        for plugin in CONF.plugins:
            opts = [
                cfg.StrOpt('plugin_class', required=True),
            ]
            CONF.register_opts(opts, group='plugin:%s' % plugin)

        config.parse_configs()

        # register plugin-specific configs
        for plugin_name in CONF.plugins:
            self.plugins[plugin_name] = self._get_plugin_instance(plugin_name)

        config.parse_configs()

        titles = []
        for plugin_name in CONF.plugins:
            plugin = self.plugins[plugin_name]
            plugin.setup(CONF['plugin:%s' % plugin_name])

            title = plugin.get_title()
            if title in titles:
                # replace with specific error
                raise RuntimeError(
                    "Title of plugin '%s' isn't unique" % plugin_name)
            titles.append(title)

            LOG.info("Plugin '%s' defined and loaded" % plugin_name)

    def _get_plugin_instance(self, plugin_name):
        plugin_path = CONF['plugin:%s' % plugin_name].plugin_class
        module_path, klass = [s.strip() for s in plugin_path.split(':')]
        if not module_path or not klass:
            # TODO(slukjanov): replace with specific error
            raise RuntimeError("Incorrect plugin_class: '%s'" %
                               plugin_path)
        module = importutils.try_import(module_path)
        if not hasattr(module, klass):
            # TODO(slukjanov): replace with specific error
            raise RuntimeError("Class not found: '%s'" % plugin_path)

        plugin_class = getattr(module, klass)
        if not inspect.isclass(plugin_class):
            # TODO(slukjanov): replace with specific error
            raise RuntimeError("'%s' isn't a class" % plugin_path)

        plugin = plugin_class()
        plugin.name = plugin_name

        CONF.register_opts(plugin.get_plugin_opts(),
                           group='plugin:%s' % plugin_name)

        return plugin

    def get_plugins(self, base):
        return [
            self.plugins[plugin] for plugin in self.plugins
            if not base or issubclass(self.plugins[plugin].__class__, base)
        ]

    def get_plugin(self, plugin_name):
        return self.plugins.get(plugin_name)


PLUGINS = None


def setup_plugins():
    global PLUGINS
    PLUGINS = PluginManager()
