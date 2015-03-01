# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


def chown(instance, owner, path, run_as_root=True):
    cmd = 'chown -R %(owner)s %(path)s' % {'owner': owner, 'path': path}
    with instance.remote() as r:
        r.execute_command(cmd, run_as_root=run_as_root)


def re_configure_sh(instance, cluster_context):
    with instance.remote() as r:
        command = '%s -R' % cluster_context.configure_sh_path
        r.execute_command(command, run_as_root=True)
