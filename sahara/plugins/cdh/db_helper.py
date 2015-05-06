# Copyright (c) 2015 Intel Corporation.
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

import uuid

import six

from sahara import conductor
from sahara import context

conductor = conductor.API


def get_password_from_db(cluster, pwname):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster.id)
    passwd = cluster.extra.get(pwname) if cluster.extra else None
    if passwd:
        return passwd

    passwd = six.text_type(uuid.uuid4())
    extra = cluster.extra.to_dict() if cluster.extra else {}
    extra[pwname] = passwd
    cluster = conductor.cluster_update(ctx, cluster, {'extra': extra})
    return passwd


def get_cm_password(cluster):
    return get_password_from_db(cluster, 'cm_password')


def remote_execute_db_script(remote, script_content):
    script_name = 'script_to_exec.sql'
    remote.write_file_to(script_name, script_content)

    psql_cmd = ('PGPASSWORD=$(sudo head -1 /var/lib/cloudera-scm-server-db'
                '/data/generated_password.txt) psql -U cloudera-scm '
                '-h localhost -p 7432 -d scm -f %s') % script_name
    remote.execute_command(psql_cmd)
    remote.execute_command('rm %s' % script_name)
