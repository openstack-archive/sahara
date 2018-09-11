# Copyright (c) 2018 Red Hat, Inc.
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

from sahara.swift import swift_helper


def install_ssl_certs(instances, **kwargs):
    swift_helper.install_ssl_certs(instances)


def get_swift_configs(**kwargs):
    return swift_helper.get_swift_configs()


def read_default_swift_configs(**kwargs):
    return swift_helper.read_default_swift_configs()
