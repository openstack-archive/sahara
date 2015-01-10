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

import sahara.exceptions as ex
from sahara.i18n import _
from sahara.plugins import base as plugin_base


CONVERT_TO_TEMPLATE_SCHEMA = None


def check_convert_to_template(plugin_name, version, **kwargs):
    if not plugin_base.PLUGINS.is_plugin_implements(plugin_name, 'convert'):
        raise ex.InvalidReferenceException(
            _("Requested plugin '%s' doesn't support converting config files "
              "to cluster templates") % plugin_name)
