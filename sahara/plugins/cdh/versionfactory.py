# Copyright (c) 2014 Mirantis, Inc.
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

import os
import re

from sahara.utils import general


class VersionFactory(object):
    versions = None
    modules = None
    initialized = False

    @staticmethod
    def get_instance():
        if not VersionFactory.initialized:
            src_dir = os.path.join(os.path.dirname(__file__), '')
            versions = (
                [name[1:].replace('_', '.')
                 for name in os.listdir(src_dir)
                 if (os.path.isdir(os.path.join(src_dir, name))
                     and re.match(r'^v\d+(_\d+)*$', name))])
            versions.sort(key=general.natural_sort_key)
            VersionFactory.versions = versions

            VersionFactory.modules = {}
            for version in VersionFactory.versions:
                module_name = 'sahara.plugins.cdh.v%s.versionhandler' % (
                    version.replace('.', '_'))
                module_class = getattr(
                    __import__(module_name, fromlist=['sahara']),
                    'VersionHandler')
                module = module_class()
                key = version.replace('_', '.')
                VersionFactory.modules[key] = module

            VersionFactory.initialized = True

        return VersionFactory()

    def get_versions(self):
        return VersionFactory.versions

    def get_version_handler(self, version):
        return VersionFactory.modules[version]
