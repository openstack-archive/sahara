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

from oslo_config import cfg
from oslo_log import log as logging
import six
from stevedore import enabled

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.utils import resources


LOG = logging.getLogger(__name__)

opts = [
    cfg.ListOpt('plugins',
                default=['vanilla', 'hdp', 'spark', 'cdh'],
                help='List of plugins to be loaded. Sahara preserves the '
                     'order of the list when returning it.'),
]

CONF = cfg.CONF
CONF.register_opts(opts)


def required(fun):
    return abc.abstractmethod(fun)


def required_with_default(fun):
    return fun


def optional(fun):
    fun.__not_implemented__ = True
    return fun


@six.add_metaclass(abc.ABCMeta)
class PluginInterface(resources.BaseResource):
    __resource_name__ = 'plugin'

    name = 'plugin_interface'

    @required
    def get_title(self):
        """Plugin title

        For example:

            "Vanilla Provisioning"
        """
        pass

    @required_with_default
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
        self._load_cluster_plugins()

    def _load_cluster_plugins(self):
        config_plugins = CONF.plugins
        extension_manager = enabled.EnabledExtensionManager(
            check_func=lambda ext: ext.name in config_plugins,
            namespace='sahara.cluster.plugins',
            invoke_on_load=True
        )

        for ext in extension_manager.extensions:
            if ext.name in self.plugins:
                raise ex.ConfigurationError(
                    _("Plugin with name '%s' already exists.") % ext.name)
            ext.obj.name = ext.name
            self.plugins[ext.name] = ext.obj
            LOG.info(_LI("Plugin {plugin_name} loaded {entry_point}").format(
                     plugin_name=ext.name,
                     entry_point=ext.entry_point_target))

        if len(self.plugins) < len(config_plugins):
            loaded_plugins = set(six.iterkeys(self.plugins))
            requested_plugins = set(config_plugins)
            raise ex.ConfigurationError(
                _("Plugins couldn't be loaded: %s") %
                ", ".join(requested_plugins - loaded_plugins))

    def get_plugins(self, base):
        return [
            self.plugins[plugin] for plugin in CONF.plugins
            if not base or issubclass(self.plugins[plugin].__class__, base)
        ]

    def get_plugin(self, plugin_name):
        return self.plugins.get(plugin_name)

    def is_plugin_implements(self, plugin_name, fun_name):
        plugin = self.get_plugin(plugin_name)

        fun = getattr(plugin, fun_name)

        if not (fun and callable(fun)):
            return False

        return not hasattr(fun, '__not_implemented__')


PLUGINS = None


def setup_plugins():
    global PLUGINS
    PLUGINS = PluginManager()
