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


from oslo_utils import uuidutils

from sahara import conductor
from sahara import context
from sahara.service.castellan import utils as key_manager
from sahara.utils import files

CM_PASSWORD = 'cm_password'
HIVE_DB_PASSWORD = 'hive_db_password'
SENTRY_DB_PASSWORD = 'sentry_db_password'

conductor = conductor.API


def delete_password_from_keymanager(cluster, pwname):
    """delete the named password from the key manager

    This function will lookup the named password in the cluster entry
    and delete it from the key manager.

    :param cluster: The cluster record containing the password
    :param pwname: The name associated with the password
    """
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster.id)
    key_id = cluster.extra.get(pwname) if cluster.extra else None
    if key_id is not None:
        key_manager.delete_key(key_id, ctx)


def delete_passwords_from_keymanager(cluster):
    """delete all passwords associated with a cluster

    This function will remove all passwords stored in a cluster database
    entry from the key manager.

    :param cluster: The cluster record containing the passwords
    """
    delete_password_from_keymanager(cluster, CM_PASSWORD)
    delete_password_from_keymanager(cluster, HIVE_DB_PASSWORD)
    delete_password_from_keymanager(cluster, SENTRY_DB_PASSWORD)


def get_password_from_db(cluster, pwname):
    """return a password for the named entry

    This function will return, or create and return, a password for the
    named entry. It will store the password in the key manager and use
    the ID in the database entry.

    :param cluster: The cluster record containing the password
    :param pwname: The entry name associated with the password
    :returns: The cleartext password
    """
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster.id)
    passwd = cluster.extra.get(pwname) if cluster.extra else None
    if passwd:
        return key_manager.get_secret(passwd, ctx)

    passwd = uuidutils.generate_uuid()
    extra = cluster.extra.to_dict() if cluster.extra else {}
    extra[pwname] = key_manager.store_secret(passwd, ctx)
    conductor.cluster_update(ctx, cluster, {'extra': extra})
    return passwd


def get_cm_password(cluster):
    return get_password_from_db(cluster, CM_PASSWORD)


def remote_execute_db_script(remote, script_content):
    script_name = 'script_to_exec.sql'
    remote.write_file_to(script_name, script_content)

    psql_cmd = ('PGPASSWORD=$(sudo head -1 /var/lib/cloudera-scm-server-db'
                '/data/generated_password.txt) psql -U cloudera-scm '
                '-h localhost -p 7432 -d scm -f %s') % script_name
    remote.execute_command(psql_cmd)
    remote.execute_command('rm %s' % script_name)


def get_hive_db_password(cluster):
    return get_password_from_db(cluster, 'hive_db_password')


def get_sentry_db_password(cluster):
    return get_password_from_db(cluster, 'sentry_db_password')


def create_hive_database(cluster, remote):
    db_password = get_hive_db_password(cluster)
    create_db_script = files.get_file_text(
        'plugins/cdh/db_resources/create_hive_db.sql')
    create_db_script = create_db_script % db_password
    remote_execute_db_script(remote, create_db_script)


def create_sentry_database(cluster, remote):
    db_password = get_sentry_db_password(cluster)
    create_db_script = files.get_file_text(
        'plugins/cdh/db_resources/create_sentry_db.sql')
    create_db_script = create_db_script % db_password
    remote_execute_db_script(remote, create_db_script)
