# Copyright (c) 2013 Hortonworks, Inc.
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

from sahara.utils import general


class VersionHandlerFactory(object):
    versions = None
    modules = None
    initialized = False

    @staticmethod
    def get_instance():
        if not VersionHandlerFactory.initialized:
            src_dir = os.path.join(os.path.dirname(__file__), '')
            versions = [name[8:].replace('_', '.')
                        for name in os.listdir(src_dir)
                        if os.path.isdir(os.path.join(src_dir, name))
                        and name.startswith('version_')]
            versions.sort(key=general.natural_sort_key)
            VersionHandlerFactory.versions = versions

            VersionHandlerFactory.modules = {}
            for version in VersionHandlerFactory.versions:
                module_name = ('sahara.plugins.hdp.versions.version_{0}.'
                               'versionhandler'.format(
                                   version.replace('.', '_')))
                module_class = getattr(
                    __import__(module_name, fromlist=['sahara']),
                    'VersionHandler')
                module = module_class()
                # would prefer to use __init__ or some constructor, but keep
                # getting exceptions...
                module._set_version(version)
                VersionHandlerFactory.modules[version] = module

            VersionHandlerFactory.initialized = True

        return VersionHandlerFactory()

    def get_versions(self):
        return VersionHandlerFactory.versions

    def get_version_handler(self, version):
        return VersionHandlerFactory.modules[version]
