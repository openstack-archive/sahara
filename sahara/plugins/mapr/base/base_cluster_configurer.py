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


import abc
import os

from oslo_log import log as logging
import six

from sahara import conductor
from sahara import context
from sahara.i18n import _LI
from sahara.i18n import _LW
import sahara.plugins.mapr.abstract.configurer as ac
import sahara.plugins.mapr.services.management.management as mng
import sahara.plugins.mapr.services.mapreduce.mapreduce as mr
from sahara.plugins.mapr.services.maprfs import maprfs
from sahara.plugins.mapr.services.mysql import mysql
import sahara.plugins.mapr.services.yarn.yarn as yarn
import sahara.plugins.mapr.util.general as util
from sahara.topology import topology_helper as th
import sahara.utils.configs as sahara_configs


LOG = logging.getLogger(__name__)
conductor = conductor.API

_MAPR_HOME = '/opt/mapr'
_JAVA_HOME = '/usr/java/jdk1.7.0_51'
_CONFIGURE_SH_TIMEOUT = 600
_SET_MODE_CMD = 'maprcli cluster mapreduce set -mode '

_TOPO_SCRIPT = 'plugins/mapr/resources/topology.sh'
INSTALL_JAVA_SCRIPT = 'plugins/mapr/resources/install_java.sh'
INSTALL_SCALA_SCRIPT = 'plugins/mapr/resources/install_scala.sh'
INSTALL_MYSQL_CLIENT = 'plugins/mapr/resources/install_mysql_client.sh'
ADD_MAPR_REPO_SCRIPT = 'plugins/mapr/resources/add_mapr_repo.sh'

SERVICE_INSTALL_PRIORITY = [
    mng.Management(),
    yarn.YARNv251(),
    yarn.YARNv241(),
    mr.MapReduce(),
    maprfs.MapRFS(),
]


@six.add_metaclass(abc.ABCMeta)
class BaseConfigurer(ac.AbstractConfigurer):
    def configure(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        self._configure_ssh_connection(cluster_context, instances)
        self._install_mapr_repo(cluster_context, instances)
        if not cluster_context.is_prebuilt:
            self._prepare_bare_image(cluster_context, instances)
        self._install_services(cluster_context, instances)
        self._configure_topology(cluster_context, instances)
        self._configure_database(cluster_context, instances)
        self._configure_services(cluster_context, instances)
        self._configure_sh_cluster(cluster_context, instances)
        self._set_cluster_mode(cluster_context)
        self._write_config_files(cluster_context, instances)
        self._configure_environment(cluster_context, instances)
        self._update_cluster_info(cluster_context)

    def update(self, cluster_context, instances=None):
        LOG.debug('Configuring existing instances')
        instances = instances or cluster_context.get_instances()
        existing = cluster_context.existing_instances()
        self._configure_topology(cluster_context, existing)
        if cluster_context.has_control_nodes(instances):
            self._configure_sh_cluster(cluster_context, existing)
        self._write_config_files(cluster_context, existing)
        self._update_services(cluster_context, existing)
        self._restart_services(cluster_context)
        LOG.info(_LI('Existing instances successfully configured'))

    def _configure_services(self, cluster_context, instances):
        for service in cluster_context.cluster_services:
            service.configure(cluster_context, instances)

    def _install_services(self, cluster_context, instances):
        for service in self._service_install_sequence(cluster_context):
            service.install(cluster_context, instances)

    def _service_install_sequence(self, cluster_context):
        def key(service):
            if service in SERVICE_INSTALL_PRIORITY:
                return SERVICE_INSTALL_PRIORITY.index(service)
            return -1

        return sorted(cluster_context.cluster_services, key=key, reverse=True)

    def _prepare_bare_image(self, cluster_context, instances):
        LOG.debug('Preparing bare image')
        d_name = cluster_context.distro.name

        LOG.debug('Installing Java')
        util.execute_on_instances(
            instances, util.run_script, INSTALL_JAVA_SCRIPT, 'root', d_name)
        LOG.debug('Installing Scala')
        util.execute_on_instances(
            instances, util.run_script, INSTALL_SCALA_SCRIPT, 'root', d_name)
        LOG.debug('Installing MySQL client')
        util.execute_on_instances(
            instances, util.run_script, INSTALL_MYSQL_CLIENT, 'root', d_name)
        LOG.debug('Bare images successfully prepared')

    def _configure_topology(self, context, instances):
        def write_file(instance, path, data):
            with instance.remote() as r:
                r.write_file_to(path, data, run_as_root=True)

        LOG.debug('Configuring cluster topology')
        is_node_aware = context.is_node_aware
        if is_node_aware:
            topo = th.generate_topology_map(context.cluster, is_node_aware)
            topo = '\n'.join(['%s %s' % i for i in six.iteritems(topo)])
            data_path = '%s/topology.data' % context.mapr_home
            util.execute_on_instances(instances, write_file, data_path, topo)
            util.execute_on_instances(
                instances, util.run_script, _TOPO_SCRIPT, 'root', data_path)
        else:
            LOG.debug('Data locality is disabled.')
        LOG.info(_LI('Cluster topology successfully configured'))

    def _write_config_files(self, cluster_context, instances):
        LOG.debug('Writing config files')

        def get_node_groups(instances):
            return util.unique_list(instances, lambda i: i.node_group)

        for ng in get_node_groups(instances):
            ng_services = cluster_context.get_cluster_services(ng)
            ng_user_configs = ng.configuration()
            ng_default_configs = cluster_context.get_services_configs_dict(
                ng_services)
            ng_configs = sahara_configs.merge_configs(
                ng_default_configs, ng_user_configs)
            ng_config_files = dict()
            for service in ng_services:
                service_conf_files = service.get_config_files(
                    cluster_context=cluster_context,
                    configs=ng_configs[service.ui_name],
                    instance=ng.instances[0]
                )
                LOG.debug('Rendering {ui_name} config files'.format(
                    ui_name=service.ui_name))
                for conf_file in service_conf_files:
                    ng_config_files.update({
                        conf_file.remote_path: conf_file.render()
                    })

            ng_instances = filter(lambda i: i in instances, ng.instances)
            self._write_ng_config_files(ng_instances, ng_config_files)
        LOG.debug('Config files successfully wrote')

    def _write_ng_config_files(self, instances, conf_files):
        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('write-config-files-%s' % instance.id,
                         self._write_config_files_instance, instance,
                         conf_files)

    def _configure_environment(self, cluster_context, instances):
        self.configure_general_environment(cluster_context, instances)
        self._post_install_services(cluster_context, instances)

    def _configure_database(self, cluster_context, instances):
        mysql_instance = mysql.MySQL.get_db_instance(cluster_context)
        distro_name = cluster_context.distro.name
        mysql.MySQL.install_mysql(mysql_instance, distro_name)
        mysql.MySQL.start_mysql_server(cluster_context)
        mysql.MySQL.create_databases(cluster_context, instances)

    @staticmethod
    def _write_config_files_instance(instance, config_files):
        paths = six.iterkeys(config_files)
        with instance.remote() as r:
            for path in paths:
                r.execute_command('mkdir -p ' + os.path.dirname(path),
                                  run_as_root=True)
            r.write_files_to(config_files, run_as_root=True)

    def _post_install_services(self, cluster_context, instances):
        LOG.debug('Executing service post install hooks')
        for s in cluster_context.cluster_services:
            s.post_install(cluster_context, instances)
        LOG.info(_LI('Post install hooks execution successfully executed'))

    def _update_cluster_info(self, cluster_context):
        LOG.debug('Updating UI information.')
        info = dict()
        for service in cluster_context.cluster_services:
            for uri_info in service.ui_info:
                title, process, url = uri_info
                info.update({
                    title: {
                        'WebUI': url % cluster_context.get_instance_ip(process)
                    }
                })

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster_context.cluster, {'info': info})

    def configure_general_environment(self, cluster_context, instances=None):
        LOG.debug('Executing post configure hooks')

        if not instances:
            instances = cluster_context.get_instances()

        def set_user_password(instance):
            LOG.debug('Setting password for user "mapr"')
            if self.mapr_user_exists(instance):
                with instance.remote() as r:
                    r.execute_command(
                        'echo "%s:%s"|chpasswd' % ('mapr', 'mapr'),
                        run_as_root=True)
            else:
                LOG.warning(_LW('User "mapr" does not exists'))

        def create_home_mapr(instance):
            target_path = '/home/mapr'
            LOG.debug("Creating home directory for user 'mapr'")
            args = {'path': target_path}
            cmd = 'mkdir -p %(path)s && chown mapr:mapr %(path)s' % args
            if self.mapr_user_exists(instance):
                with instance.remote() as r:
                    r.execute_command(cmd, run_as_root=True)
            else:
                LOG.warning(_LW('User "mapr" does not exists'))

        util.execute_on_instances(instances, set_user_password)
        util.execute_on_instances(instances, create_home_mapr)

    def _configure_sh_cluster(self, cluster_context, instances):
        LOG.debug('Executing configure.sh')

        if not instances:
            instances = cluster_context.get_instances()
        script = cluster_context.configure_sh

        db_specs = dict(mysql.MySQL.METRICS_SPECS._asdict())
        db_specs.update({
            'host': mysql.MySQL.get_db_instance(cluster_context).fqdn(),
            'port': mysql.MySQL.MYSQL_SERVER_PORT,
        })

        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('configure-sh-%s' % instance.id,
                         self._configure_sh_instance, cluster_context,
                         instance, script, db_specs)
        LOG.debug('Executing configure.sh successfully completed')

    def _configure_sh_instance(self, context, instance, command, specs):
        if not self.mapr_user_exists(instance):
            command += ' --create-user'
        if context.check_for_process(instance, mng.METRICS):
            command += (' -d %(host)s:%(port)s -du %(user)s -dp %(password)s '
                        '-ds %(db_name)s') % specs
        with instance.remote() as r:
            r.execute_command('sudo -i ' + command,
                              timeout=_CONFIGURE_SH_TIMEOUT)

    def _configure_ssh_connection(self, cluster_context, instances):
        def keep_alive_connection(instance):
            echo_param = 'echo "KeepAlive yes" >> ~/.ssh/config'
            echo_timeout = 'echo "ServerAliveInterval 60" >> ~/.ssh/config'
            with instance.remote() as r:
                r.execute_command(echo_param)
                r.execute_command(echo_timeout)

        util.execute_on_instances(instances, keep_alive_connection)

    def mapr_user_exists(self, instance):
            with instance.remote() as r:
                ec, out = r.execute_command(
                    'id -u mapr', run_as_root=True, raise_when_error=False)
            return ec == 0

    def post_start(self, c_context, instances=None):
        instances = instances or c_context.get_instances()
        LOG.debug('Executing service post start hooks')
        for service in c_context.cluster_services:
            updated = c_context.filter_instances(instances, service=service)
            service.post_start(c_context, updated)
        LOG.debug('Post start hooks execution successfully executed')

    def _set_cluster_mode(self, cluster_context):
        cluster_mode = cluster_context.cluster_mode
        if not cluster_mode:
            return
        cldb = cluster_context.get_instance(maprfs.CLDB)
        with cldb.remote() as r:
            cmd = 'sudo -u mapr maprcli cluster mapreduce set -mode %s'
            r.execute_command(cmd % cluster_mode)

    def _install_mapr_repo(self, cluster_context, instances):
        d_name = cluster_context.distro.name
        util.execute_on_instances(
            instances, util.run_script, ADD_MAPR_REPO_SCRIPT, 'root', d_name,
            **cluster_context.mapr_repos)

    def _update_services(self, c_context, instances):
        for service in c_context.cluster_services:
            updated = c_context.filter_instances(instances, service=service)
            service.update(c_context, updated)

    def _restart_services(self, cluster_context):
        restart = cluster_context.should_be_restarted
        for service, instances in six.iteritems(restart):
            service.restart(util.unique_list(instances))
