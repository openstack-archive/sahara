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

from os import path

import pkg_resources as pkg

from sahara import version


def get_file_text(file_name, package='sahara'):
    full_name = pkg.resource_filename(
        package, file_name)
    return open(full_name).read()


def get_file_binary(file_name):
    full_name = pkg.resource_filename(
        version.version_info.package, file_name)
    return open(full_name, "rb").read()


def try_get_file_text(file_name, package='sahara'):
    full_name = pkg.resource_filename(
        package, file_name)
    return (
        open(full_name, "rb").read()
        if path.isfile(full_name) else False)
