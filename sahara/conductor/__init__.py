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

from oslo_config import cfg

from sahara.conductor import api as conductor_api
from sahara.i18n import _


def Api(use_local=True, **kwargs):
    """Creates local or remote conductor Api.

    Creation of local or remote conductor Api depends on passed arg 'use_local'
    and config option 'use_local' in 'conductor' group.
    """
    if cfg.CONF.conductor.use_local or use_local:
        api = conductor_api.LocalApi
    else:
        raise NotImplementedError(
            _("Remote conductor isn't implemented yet."))
        # api = conductor.RemoteApi

    return api(**kwargs)


API = Api()
