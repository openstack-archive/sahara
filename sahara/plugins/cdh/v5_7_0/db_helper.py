# Copyright (c) 2016 Mirantis Inc.
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

from sahara.plugins.cdh import db_helper as dh
from sahara.utils import files


def get_hive_db_password(cluster):
    return dh.get_password_from_db(cluster, 'hive_db_password')


def get_sentry_db_password(cluster):
    return dh.get_password_from_db(cluster, 'sentry_db_password')


def create_hive_database(cluster, remote):
    db_password = get_hive_db_password(cluster)
    create_db_script = files.get_file_text(
        'plugins/cdh/v5_7_0/resources/create_hive_db.sql')
    create_db_script = create_db_script % db_password
    dh.remote_execute_db_script(remote, create_db_script)


def create_sentry_database(cluster, remote):
    db_password = get_sentry_db_password(cluster)
    create_db_script = files.get_file_text(
        'plugins/cdh/v5_7_0/resources/create_sentry_db.sql')
    create_db_script = create_db_script % db_password
    dh.remote_execute_db_script(remote, create_db_script)
