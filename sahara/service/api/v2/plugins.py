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

from sahara.plugins import base as plugin_base


# Plugins ops


def get_plugins():
    return plugin_base.PLUGINS.get_plugins(serialized=True)


def get_plugin(plugin_name, version=None):
    return plugin_base.PLUGINS.serialize_plugin(plugin_name, version)


def update_plugin(plugin_name, values):
    return plugin_base.PLUGINS.update_plugin(plugin_name, values)
