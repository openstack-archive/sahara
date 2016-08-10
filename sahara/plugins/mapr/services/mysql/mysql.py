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


import collections as c

from oslo_log import log as logging
import six

import sahara.plugins.mapr.domain.configuration_file as cf
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.util.general as g
import sahara.utils.files as f

LOG = logging.getLogger(__name__)

db_spec = c.namedtuple('DatabaseSpec', ['db_name', 'user', 'password'])


class MySQL(s.Service):
    METRICS_SPECS = db_spec('metrics', 'maprmetrics', 'mapr')
    HUE_SPECS = db_spec('hue', 'maprhue', 'mapr')
    METASTORE_SPECS = db_spec('metastore', 'maprmetastore', 'mapr')
    RDBMS_SPECS = db_spec('rdbms', 'maprrdbms', 'mapr')
    OOZIE_SPECS = db_spec('oozie', 'maproozie', 'mapr')
    SENTRY_SPECS = db_spec('sentry', 'maprsentry', 'mapr')

    SELECT_DATA = 'mysql -uroot --skip-column-names -e "%s"| grep -E "\w+"'
    GET_DBS_LIST = SELECT_DATA % 'SHOW DATABASES'
    GET_USERS_HOSTS = (
        SELECT_DATA %
        "SELECT Host FROM mysql.user WHERE mysql.user.User='%s'"  # nosec
    )

    DRIVER_CLASS = 'com.mysql.jdbc.Driver'
    MYSQL_SERVER_PORT = 3306
    MYSQL_INSTALL_SCRIPT = 'plugins/mapr/resources/install_mysql.sh'
    INSTALL_PACKAGES_TIMEOUT = 1800

    def __init__(self):
        super(MySQL, self).__init__()
        self._ui_name = 'MySQL'

    @staticmethod
    def _get_db_daemon_name(distro, distro_version):
        if distro.lower() == 'ubuntu':
            return 'mysql'
        if distro.lower() == 'suse':
            return 'mysqld'
        if distro.lower() in ['centos', 'redhatenterpriseserver']:
            if distro_version.split('.')[0] == '7':
                return 'mariadb'
            return 'mysqld'
        return None

    @staticmethod
    def _execute_script(instance, script_path, script_text=None,
                        user='root', password=None):
        with instance.remote() as r:
            if script_text:
                r.write_file_to(script_path, script_text, run_as_root=True)
            LOG.debug('Executing SQL script {path}'.format(path=script_path))
            r.execute_command(("mysql %s %s < %s" %
                               ('-u' + user if user else '',
                                '-p' + password if password else '',
                                script_path)),
                              run_as_root=True)

    @staticmethod
    def _create_service_db(instance, specs):
        f_name = 'create_db_%s.sql' % specs.db_name
        script = MySQL._create_script_obj(f_name, 'create_database.sql',
                                          db_name=specs.db_name,
                                          user=specs.user,
                                          password=specs.password)
        MySQL._execute_script(instance, script.remote_path, script.render())

    @staticmethod
    def _create_metrics_db(instance, databases, instances):
        if MySQL.METRICS_SPECS.db_name not in databases:
            MySQL._create_service_db(instance, MySQL.METRICS_SPECS)
            MySQL._execute_script(instance=instance,
                                  script_path='/opt/mapr/bin/setup.sql')
        MySQL._grant_access(instance, MySQL.METRICS_SPECS, instances)

    @staticmethod
    def _create_hue_db(instance, databases, instances):
        if MySQL.HUE_SPECS.db_name not in databases:
            MySQL._create_service_db(instance, MySQL.HUE_SPECS)
        MySQL._grant_access(instance, MySQL.HUE_SPECS, instances)

    @staticmethod
    def _create_rdbms_db(instance, databases, instances):
        if MySQL.RDBMS_SPECS.db_name not in databases:
            MySQL._create_service_db(instance, MySQL.RDBMS_SPECS)
        MySQL._grant_access(instance, MySQL.RDBMS_SPECS, instances)

    @staticmethod
    def _create_metastore_db(instance, cluster_context, databases, instances):
        hive_meta = cluster_context.get_instance('HiveMetastore')

        if not hive_meta:
            return

        db_name = MySQL.METASTORE_SPECS.db_name
        if db_name not in databases:
            MySQL._create_service_db(instance, MySQL.METASTORE_SPECS)
        MySQL._grant_access(instance, MySQL.METASTORE_SPECS, instances)

    @staticmethod
    def _create_oozie_db(instance, databases, instances):
        if MySQL.OOZIE_SPECS.db_name not in databases:
            MySQL._create_service_db(instance, MySQL.OOZIE_SPECS)
        MySQL._grant_access(instance, MySQL.OOZIE_SPECS, instances)

    @staticmethod
    def _create_sentry_db(instance, cluster_context, databases, instances):
        sentry_instance = cluster_context.get_instance('Sentry')
        if not sentry_instance:
            return
        if MySQL.SENTRY_SPECS.db_name not in databases:
            MySQL._create_service_db(instance, MySQL.SENTRY_SPECS)
        MySQL._grant_access(instance, MySQL.SENTRY_SPECS, instances)

    @staticmethod
    def start_mysql_server(cluster_context):
        LOG.debug('Starting MySQL Server')
        instance = MySQL.get_db_instance(cluster_context)
        distro = cluster_context.distro
        distro_version = cluster_context.distro_version
        with instance.remote() as r:
            r.execute_command(('service %s restart' %
                               MySQL._get_db_daemon_name(distro.name,
                                                         distro_version)),
                              run_as_root=True)
        LOG.debug('MySQL Server successfully started')

    @staticmethod
    def get_databases_list(db_instance):
        with db_instance.remote() as r:
            ec, out = r.execute_command(MySQL.GET_DBS_LIST)
            if out:
                return out.splitlines()
        return list()

    @staticmethod
    def get_user_hosts(db_instance, username):
        with db_instance.remote() as r:
            ec, out = r.execute_command(MySQL.GET_USERS_HOSTS % username)
            if out:
                return out.splitlines()
        return list()

    @staticmethod
    def get_db_instance(cluster_context):
        return cluster_context.oozie_server

    @staticmethod
    def create_databases(cluster_context, instances):
        db_instance = MySQL.get_db_instance(cluster_context)
        databases = MySQL.get_databases_list(db_instance)
        MySQL._create_metrics_db(db_instance, databases, instances)
        MySQL._create_hue_db(db_instance, databases, instances)
        MySQL._create_rdbms_db(db_instance, databases, instances)
        MySQL._create_oozie_db(db_instance, databases, instances)
        MySQL._create_metastore_db(
            db_instance, cluster_context, databases, instances)
        MySQL._create_sentry_db(db_instance, cluster_context, databases,
                                instances)

    @staticmethod
    def _create_script_obj(filename, template, **kwargs):
        script = cf.TemplateFile(filename)
        script.remote_path = '/tmp/'
        script.parse(f.get_file_text(
            'plugins/mapr/services/mysql/resources/%s' % template))
        for k, v in six.iteritems(kwargs):
            script.add_property(k, v)
        return script

    @staticmethod
    def _grant_access(instance, specs, instances):
        f_name = 'grant_access_%s.sql' % specs.db_name
        ips = [i.internal_ip for i in instances]
        user_hosts = MySQL.get_user_hosts(instance, specs.user)
        script = MySQL._create_script_obj(f_name, 'grant_access.sql',
                                          hosts=set(ips) - set(user_hosts),
                                          db_name=specs.db_name,
                                          user=specs.user,
                                          password=specs.password)
        MySQL._execute_script(instance, script.remote_path, script.render())

    @staticmethod
    def install_mysql(instance, distro_name):
        g.run_script(instance, MySQL.MYSQL_INSTALL_SCRIPT, 'root', distro_name)
