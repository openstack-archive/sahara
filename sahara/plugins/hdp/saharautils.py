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


def get_host_role(host):
    if hasattr(host, 'role'):
        return host.role
    else:
        return host.node_group.name


def inject_remote(param_name):
    def handle(func):
        def call(self, *args, **kwargs):
            with self.instance.remote() as r:
                newkwargs = kwargs.copy()
                newkwargs[param_name] = r
                return func(self, *args, **newkwargs)

        return call
    return handle
