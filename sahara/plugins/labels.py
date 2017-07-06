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

import copy

from oslo_log import log as logging

from sahara import conductor as cond
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _

conductor = cond.API
LOG = logging.getLogger(__name__)


STABLE = {
    'name': 'stable',
    'mutable': False,
    'description': "Indicates that plugin or its version are stable to be used"
}

DEPRECATED = {
    'name': 'deprecated',
    'mutable': False,
    'description': "Plugin or its version is deprecated and will be removed "
                   "in future releases. Please, consider to use another "
                   "plugin or its version."
}

ENABLED = {
    'name': 'enabled',
    'mutable': True,
    'description': "Plugin or its version is enabled and can be used by user."
}

HIDDEN = {
    'name': 'hidden',
    'mutable': True,
    'description': "Existence of plugin or its version is hidden, but "
                   "still can be used for cluster creation by CLI and "
                   "directly by client."
}

PLUGIN_LABELS_SCOPE = 'plugin_labels'
VERSION_LABELS_SCOPE = 'version_labels'
MUTABLE = 'mutable'

LABEL_OBJECT = {
    'type': 'object',
    'properties': {
        'status': {
            'type': 'boolean',
        }
    },
    "additionalProperties": False,
}


class LabelHandler(object):
    def __init__(self, loaded_plugins):
        self.plugins = loaded_plugins

    def get_plugin_update_validation_jsonschema(self):
        schema = {
            'type': 'object', "additionalProperties": False,
            'properties': {
                VERSION_LABELS_SCOPE: {
                    'type': 'object', 'additionalProperties': False,
                },
            },
        }
        ln = [label['name'] for label in self.get_labels()]
        labels_descr_object = {
            'type': 'object',
            "properties": {name: copy.deepcopy(LABEL_OBJECT) for name in ln},
            "additionalProperties": False
        }
        schema['properties'][PLUGIN_LABELS_SCOPE] = copy.deepcopy(
            labels_descr_object)
        all_versions = []
        for plugin_name in self.plugins.keys():
            plugin = self.plugins[plugin_name]
            all_versions.extend(plugin.get_versions())
        all_versions = set(all_versions)
        schema['properties'][VERSION_LABELS_SCOPE]['properties'] = {
            ver: copy.deepcopy(labels_descr_object) for ver in all_versions
        }
        return schema

    def get_default_label_details(self, plugin_name):
        plugin = self.plugins.get(plugin_name)
        return plugin.get_labels()

    def get_label_details(self, plugin_name):
        try:
            plugin = conductor.plugin_get(context.ctx(), plugin_name)
        except Exception:
            LOG.error("Unable to retrieve plugin data from database")
            plugin = None
        if not plugin:
            plugin = self.get_default_label_details(plugin_name)
        fields = ['name', 'id', 'updated_at', 'created_at']
        for field in fields:
            if field in plugin:
                del plugin[field]
        return plugin

    def get_label_full_details(self, plugin_name):
        return self.expand_data(self.get_label_details(plugin_name))

    def get_labels(self):
        return [HIDDEN, STABLE, ENABLED, DEPRECATED]

    def get_labels_map(self):
        return {
            label['name']: label for label in self.get_labels()
        }

    def expand_data(self, plugin):
        plugin_labels = plugin.get(PLUGIN_LABELS_SCOPE)
        labels_map = self.get_labels_map()
        for key in plugin_labels.keys():
            key_desc = labels_map.get(key)
            plugin_labels[key].update(key_desc)
            del plugin_labels[key]['name']

        for version in plugin.get(VERSION_LABELS_SCOPE):
            vers_labels = plugin.get(VERSION_LABELS_SCOPE).get(version)
            for key in vers_labels.keys():
                key_desc = labels_map.get(key)
                vers_labels[key].update(key_desc)
                del vers_labels[key]['name']

        return plugin

    def _validate_labels_update(self, default_data, update_values):
        for label in update_values.keys():
            if label not in default_data.keys():
                raise ex.InvalidDataException(
                    _("Label '%s' can't be updated because it's not "
                      "available for plugin or its version") % label)
            if not default_data[label][MUTABLE]:
                raise ex.InvalidDataException(
                    _("Label '%s' can't be updated because it's not "
                      "mutable") % label)

    def validate_plugin_update(self, plugin_name, values):
        plugin = self.plugins[plugin_name]
        # it's important to get full details since we have mutability
        default = self.get_label_full_details(plugin_name)
        if values.get(PLUGIN_LABELS_SCOPE):
            pl = values.get(PLUGIN_LABELS_SCOPE)
            self._validate_labels_update(default[PLUGIN_LABELS_SCOPE], pl)

        if values.get(VERSION_LABELS_SCOPE):
            vl = values.get(VERSION_LABELS_SCOPE)
            for version in vl.keys():
                if version not in plugin.get_versions():
                    raise ex.InvalidDataException(
                        _("Unknown plugin version '%(version)s' of "
                          "%(plugin)s") % {
                            'version': version, 'plugin': plugin_name})
                self._validate_labels_update(
                    default[VERSION_LABELS_SCOPE][version], vl[version])

    def update_plugin(self, plugin_name, values):
        ctx = context.ctx()
        current = self.get_label_details(plugin_name)
        if not conductor.plugin_get(ctx, plugin_name):
            current['name'] = plugin_name
            conductor.plugin_create(ctx, current)
            del current['name']

        if values.get(PLUGIN_LABELS_SCOPE):
            for label in values.get(PLUGIN_LABELS_SCOPE).keys():
                current[PLUGIN_LABELS_SCOPE][label].update(
                    values.get(PLUGIN_LABELS_SCOPE).get(label))
        else:
            del current[PLUGIN_LABELS_SCOPE]

        if values.get(VERSION_LABELS_SCOPE):
            vl = values.get(VERSION_LABELS_SCOPE)
            for version in vl.keys():
                for label in vl.get(version).keys():
                    current[VERSION_LABELS_SCOPE][version][label].update(
                        vl[version][label])
        else:
            del current[VERSION_LABELS_SCOPE]

        conductor.plugin_update(context.ctx(), plugin_name, current)

    def validate_plugin_labels(self, plugin_name, version):
        details = self.get_label_details(plugin_name)
        plb = details.get(PLUGIN_LABELS_SCOPE, {})
        if not plb.get('enabled', {}).get('status'):
            raise ex.InvalidReferenceException(
                _("Plugin %s is not enabled") % plugin_name)

        if plb.get('deprecated', {}).get('status', False):
            LOG.warning("Plugin %s is deprecated and can be removed in "
                        "the next release", plugin_name)

        vlb = details.get(VERSION_LABELS_SCOPE, {}).get(version, {})
        if not vlb.get('enabled', {}).get('status'):
            raise ex.InvalidReferenceException(
                _("Version %(version)s of plugin %(plugin)s is not enabled")
                % {'version': version, 'plugin': plugin_name})

        if vlb.get('deprecated', {}).get('status', False):
            LOG.warning("Using version %(version)s of plugin %(plugin)s is "
                        "deprecated and can removed in next release",
                        {'version': version, 'plugin': plugin_name})
