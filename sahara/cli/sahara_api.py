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

from sahara.utils import patches
patches.patch_all()

import os
import sys

import oslo_i18n
from oslo_log import log as logging

# If ../sahara/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir,
                               'sahara',
                               '__init__.py')):
    sys.path.insert(0, possible_topdir)


# NOTE(slukjanov): i18n.enable_lazy() must be called before
#                  sahara.utils.i18n._() is called to ensure it has the desired
#                  lazy lookup behavior.
oslo_i18n.enable_lazy()


import sahara.main as server


LOG = logging.getLogger(__name__)


def main():
    server.setup_common(possible_topdir, 'API')

    app = server.make_app()

    server.setup_sahara_api('distributed')
    server.setup_auth_policy()

    launcher = server.get_process_launcher()
    api_service = server.SaharaWSGIService("sahara-api", app)
    server.launch_api_service(launcher, api_service)
